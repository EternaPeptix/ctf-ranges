// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "./common/Mocks.sol";

/// C4 — The Mirror.
/// Read-only reentrancy on an LP "virtual price". `removeLiquidity` decrements
/// the LP supply and sends ETH to the caller BEFORE it has transferred out the
/// token side — so during that ETH callback the pool's `getVirtualPrice()` is
/// transiently inflated. A lending desk that reads the virtual price live, while
/// re-entered, values the attacker's LP collateral at the bogus mark and lets
/// them borrow the desk dry. (Curve read-only reentrancy.)
///
/// Isolated training range. Do not deploy.

/// A 2-asset (ETH + token) "stable" pool with an ERC20-style LP share.
contract StablePool {
    MockERC20 public token;
    uint256 public totalLP;
    mapping(address => uint256) public lp;
    mapping(address => mapping(address => uint256)) public lpAllowance;

    constructor(MockERC20 t) { token = t; }

    function addLiquidity(uint256 tokenAmt) external payable {
        uint256 shares = totalLP == 0 ? msg.value
                                      : msg.value * totalLP / (address(this).balance - msg.value);
        token.transferFrom(msg.sender, address(this), tokenAmt);
        lp[msg.sender] += shares;
        totalLP += shares;
    }

    /// (ETH + token) value per LP share, 1e18. Read by the lending desk.
    function getVirtualPrice() public view returns (uint256) {
        if (totalLP == 0) return 1e18;
        uint256 value = address(this).balance + token.balanceOf(address(this));
        return value * 1e18 / totalLP;
    }

    function removeLiquidity(uint256 shares) external {
        uint256 ethOut = address(this).balance * shares / totalLP;
        uint256 tokOut = token.balanceOf(address(this)) * shares / totalLP;
        lp[msg.sender] -= shares;
        totalLP -= shares;                               // supply reduced first...
        (bool ok, ) = msg.sender.call{value: ethOut}(""); // ...then the ETH callback...
        require(ok, "eth out");
        token.transfer(msg.sender, tokOut);               // ...token sent only after
    }

    // --- ERC20-style LP share plumbing ---
    function transfer(address to, uint256 amt) external returns (bool) {
        lp[msg.sender] -= amt; lp[to] += amt; return true;
    }
    function approve(address sp, uint256 amt) external returns (bool) {
        lpAllowance[msg.sender][sp] = amt; return true;
    }
    function transferFrom(address f, address t, uint256 amt) external returns (bool) {
        uint256 a = lpAllowance[f][msg.sender];
        require(a >= amt, "lp allowance");
        if (a != type(uint256).max) lpAllowance[f][msg.sender] = a - amt;
        lp[f] -= amt; lp[t] += amt; return true;
    }

    receive() external payable {}
}

/// Lends ETH against StablePool LP, valued at the live virtual price (the bug).
contract LendingDesk {
    StablePool public pool;
    mapping(address => uint256) public collateral;

    constructor(StablePool p) payable { pool = p; }

    function deposit(uint256 lpAmt) external {
        pool.transferFrom(msg.sender, address(this), lpAmt);
        collateral[msg.sender] += lpAmt;
    }

    function borrow(uint256 ethAmt) external {
        // BUG: reads getVirtualPrice() live — manipulable via read-only reentrancy
        uint256 value = collateral[msg.sender] * pool.getVirtualPrice() / 1e18;
        require(value >= ethAmt, "undercollateralized");
        (bool ok, ) = msg.sender.call{value: ethAmt}("");
        require(ok, "eth out");
    }

    receive() external payable {}
}

contract MirrorSetup {
    MockERC20 public token;
    StablePool public pool;
    LendingDesk public desk;
    address constant ATTACKER = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    constructor() payable {
        token = new MockERC20("Pool LP Underlying", "pUSD", 18);
        pool = new StablePool(token);

        // seed the pool with 1000 ETH + 1000 token  => fair virtual price 2e18
        token.mint(address(this), 1000 ether);
        token.approve(address(pool), type(uint256).max);
        pool.addLiquidity{value: 1000 ether}(1000 ether);   // 1000 LP to this setup

        // hand most of the LP to the attacker (the rest are "other LPs")
        pool.transfer(ATTACKER, 900 ether);

        // the desk holds 100 ETH to lend against LP collateral
        desk = new LendingDesk{value: 100 ether}(pool);
    }

    function isSolved() external view returns (bool) {
        return address(desk).balance == 0;
    }
}
