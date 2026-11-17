// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "./common/Mocks.sol";

/// C5 — The Mint.
/// Naive LP-token pricing. A lending desk values AMM LP collateral as
/// (reserveToken·$ + reserveUSDX·$) / totalSupply — the *spot* reserves, not a
/// manipulation-resistant fair value. Flash-borrow USDX, imbalance the pool so
/// the summed reserve value (and thus the LP price) balloons, borrow the desk
/// dry against your LP collateral, swap back, and repay the flash loan.
/// (Warp Finance / Cheese Bank.)
///
/// Isolated training range. Do not deploy.

interface IFlashBorrower {
    function onFlashLoan(uint256 amount, bytes calldata data) external;
}

/// Constant-product token<->USDX pool with an ERC20-style LP share.
contract LpAMM {
    MockERC20 public token;
    MockERC20 public usdx;
    uint256 public totalLP;
    mapping(address => uint256) public lp;
    mapping(address => mapping(address => uint256)) public lpAllowance;

    constructor(MockERC20 t, MockERC20 u) { token = t; usdx = u; }

    function reserves() public view returns (uint256 tr, uint256 ur) {
        return (token.balanceOf(address(this)), usdx.balanceOf(address(this)));
    }

    function addLiquidity(uint256 tokenAmt, uint256 usdxAmt) external returns (uint256 shares) {
        token.transferFrom(msg.sender, address(this), tokenAmt);
        usdx.transferFrom(msg.sender, address(this), usdxAmt);
        shares = totalLP == 0 ? usdxAmt : usdxAmt * totalLP / (usdx.balanceOf(address(this)) - usdxAmt);
        lp[msg.sender] += shares; totalLP += shares;
    }

    function swapUsdxForToken(uint256 usdxIn) external {
        (uint256 tr, uint256 ur) = reserves();
        usdx.transferFrom(msg.sender, address(this), usdxIn);
        uint256 out = tr - (tr * ur) / (ur + usdxIn);
        token.transfer(msg.sender, out);
    }
    function swapTokenForUsdx(uint256 tokenIn) external {
        (uint256 tr, uint256 ur) = reserves();
        token.transferFrom(msg.sender, address(this), tokenIn);
        uint256 out = ur - (tr * ur) / (tr + tokenIn);
        usdx.transfer(msg.sender, out);
    }

    function transfer(address to, uint256 amt) external returns (bool) { lp[msg.sender] -= amt; lp[to] += amt; return true; }
    function approve(address sp, uint256 amt) external returns (bool) { lpAllowance[msg.sender][sp] = amt; return true; }
    function transferFrom(address f, address t, uint256 amt) external returns (bool) {
        uint256 a = lpAllowance[f][msg.sender];
        require(a >= amt, "lp allowance");
        if (a != type(uint256).max) lpAllowance[f][msg.sender] = a - amt;
        lp[f] -= amt; lp[t] += amt; return true;
    }
}

/// Flash-lends USDX with a same-tx repayment requirement.
contract FlashLender {
    MockERC20 public usdx;
    constructor(MockERC20 u) { usdx = u; }
    function flashLoan(uint256 amount, bytes calldata data) external {
        uint256 bal0 = usdx.balanceOf(address(this));
        usdx.transfer(msg.sender, amount);
        IFlashBorrower(msg.sender).onFlashLoan(amount, data);
        require(usdx.balanceOf(address(this)) >= bal0, "flash loan not repaid");
    }
}

/// Lends USDX against LP collateral priced off spot reserves (the bug).
contract LpDesk {
    LpAMM public amm;
    MockERC20 public usdx;
    mapping(address => uint256) public collateral;

    constructor(LpAMM a, MockERC20 u) { amm = a; usdx = u; }

    function deposit(uint256 lpAmt) external {
        amm.transferFrom(msg.sender, address(this), lpAmt);
        collateral[msg.sender] += lpAmt;
    }

    // BUG: naive LP price = (reserveToken·$1 + reserveUSDX·$1) / totalLP, spot.
    function lpPrice() public view returns (uint256) {
        (uint256 tr, uint256 ur) = amm.reserves();
        return (tr + ur) * 1e18 / amm.totalLP();
    }

    function borrow(uint256 usdxAmt) external {
        uint256 value = collateral[msg.sender] * lpPrice() / 1e18;
        require(value >= usdxAmt, "undercollateralized");
        usdx.transfer(msg.sender, usdxAmt);
    }
}

contract MintSetup {
    MockERC20 public token;
    MockERC20 public usdx;
    LpAMM public amm;
    FlashLender public lender;
    LpDesk public desk;
    address constant ATTACKER = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    constructor() {
        token = new MockERC20("Blue Token", "BLU", 18);
        usdx = new MockERC20("USD X", "USDX", 18);
        amm = new LpAMM(token, usdx);

        // seed the pool 1000 token / 1000 USDX  => fair LP price 2e18
        token.mint(address(this), 1000 ether);
        usdx.mint(address(this), 1000 ether);
        token.approve(address(amm), type(uint256).max);
        usdx.approve(address(amm), type(uint256).max);
        amm.addLiquidity(1000 ether, 1000 ether);       // 1000 LP to this setup
        amm.transfer(ATTACKER, 500 ether);              // attacker's LP collateral

        lender = new FlashLender(usdx);
        usdx.mint(address(lender), 100_000 ether);      // deep flash liquidity

        desk = new LpDesk(amm, usdx);
        usdx.mint(address(desk), 2000 ether);           // 2000 USDX to lend
    }

    function isSolved() external view returns (bool) {
        return usdx.balanceOf(address(desk)) == 0;      // desk drained
    }
}
