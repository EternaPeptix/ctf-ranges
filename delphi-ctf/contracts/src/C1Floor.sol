// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "./common/Mocks.sol";

/// C1 — The Floor.
/// Chainlink `minAnswer` clamp. The collateral token's real price crashes to ~0,
/// but the aggregator floors the reported price at `minAnswer` ($1). A lending
/// market that trusts `latestAnswer()` keeps valuing the worthless token at the
/// floor, so the attacker borrows the pool dry against junk collateral.
/// (Venus / Blizz on the LUNA crash.)
///
/// Isolated training range. Do not deploy.
contract FloorLending {
    MockERC20 public collateral;    // the crashed token (18 dec)
    MockERC20 public usdx;          // the stablecoin being lent (18 dec)
    MockAggregator public oracle;   // collateral price in USD (8 dec)
    mapping(address => uint256) public deposited;

    constructor(MockERC20 c, MockERC20 u, MockAggregator o) {
        collateral = c; usdx = u; oracle = o;
    }

    function deposit(uint256 amt) external {
        collateral.transferFrom(msg.sender, address(this), amt);
        deposited[msg.sender] += amt;
    }

    function borrow(uint256 usdxAmt) external {
        // BUG: trusts the (floored) feed. collateral USD value = amt * price / 1e8.
        uint256 price = uint256(oracle.latestAnswer());
        uint256 value = deposited[msg.sender] * price / 1e8;
        require(value >= usdxAmt, "undercollateralized");
        usdx.transfer(msg.sender, usdxAmt);
    }
}

contract FloorSetup {
    MockERC20 public collateral;
    MockERC20 public usdx;
    MockAggregator public oracle;
    FloorLending public lending;
    address constant ATTACKER = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    constructor() {
        collateral = new MockERC20("Terra Moon", "MOON", 18);
        usdx = new MockERC20("USD X", "USDX", 18);
        oracle = new MockAggregator(8, 1e8, 1_000_000e8);  // minAnswer floor = $1

        oracle.setAnswer(100e8);                            // healthy: $100
        lending = new FloorLending(collateral, usdx, oracle);
        usdx.mint(address(lending), 1_000_000 ether);       // 1M USDX to lend

        // the market CRASHES to ~$0 — but the feed clamps it to the $1 floor
        oracle.setAnswer(1);                                // below minAnswer -> returns $1
        collateral.mint(ATTACKER, 1_000_000 ether);         // attacker's worthless pile
    }

    function isSolved() external view returns (bool) {
        return usdx.balanceOf(address(lending)) == 0;       // lending pool drained
    }
}
