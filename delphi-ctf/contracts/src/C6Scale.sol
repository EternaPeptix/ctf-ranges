// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "./common/Mocks.sol";

/// C6 — The Scale.
/// Oracle decimals / scaling confusion. Most Chainlink USD feeds report 8
/// decimals, so the protocol hard-codes `/ 1e8`. But this token's feed reports
/// 18 decimals, so every collateral valuation is inflated by 1e10. A tiny
/// deposit is valued as a fortune, and the attacker borrows the pool dry.
///
/// Isolated training range. Do not deploy.
contract ScaleLending {
    MockERC20 public collateral;
    MockERC20 public usdx;
    MockAggregator public oracle;   // NOTE: 18 decimals, not the assumed 8
    mapping(address => uint256) public deposited;

    constructor(MockERC20 c, MockERC20 u, MockAggregator o) {
        collateral = c; usdx = u; oracle = o;
    }

    function deposit(uint256 amt) external {
        collateral.transferFrom(msg.sender, address(this), amt);
        deposited[msg.sender] += amt;
    }

    function borrow(uint256 usdxAmt) external {
        uint256 price = uint256(oracle.latestAnswer());
        // BUG: assumes an 8-decimal feed (`/ 1e8`); this feed is 18-decimal,
        // so collateral value is overstated by 1e10.
        uint256 value = deposited[msg.sender] * price / 1e8;
        require(value >= usdxAmt, "undercollateralized");
        usdx.transfer(msg.sender, usdxAmt);
    }
}

contract ScaleSetup {
    MockERC20 public collateral;
    MockERC20 public usdx;
    MockAggregator public oracle;
    ScaleLending public lending;
    address constant ATTACKER = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    constructor() {
        collateral = new MockERC20("Decimal Token", "DEC", 18);
        usdx = new MockERC20("USD X", "USDX", 18);
        oracle = new MockAggregator(18, 0, 1e36);   // 18-decimal feed (the trap)

        oracle.setAnswer(1e18);                      // DEC is worth $1 (18-dec)
        lending = new ScaleLending(collateral, usdx, oracle);
        usdx.mint(address(lending), 1_000_000 ether); // 1M USDX to lend

        collateral.mint(ATTACKER, 1 ether);           // a single $1 token is enough
    }

    function isSolved() external view returns (bool) {
        return usdx.balanceOf(address(lending)) == 0;
    }
}
