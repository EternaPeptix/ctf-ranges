// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "./common/Mocks.sol";

/// C2 — The Stale.
/// Missing freshness check. A redemption vault buys the token from anyone at the
/// oracle price, but never checks how old that price is. The feed is frozen at an
/// old, high mark ($100) while the token has really collapsed, so the attacker
/// sells their now-worthless tokens into the vault at the stale price and drains
/// its stablecoin reserves.
///
/// Isolated training range. Do not deploy.
contract StaleVault {
    MockERC20 public token;         // the collapsed token (18 dec)
    MockERC20 public usdx;          // stablecoin reserves (18 dec)
    MockAggregator public oracle;   // token price in USD (8 dec)

    constructor(MockERC20 t, MockERC20 u, MockAggregator o) {
        token = t; usdx = u; oracle = o;
    }

    function sellToken(uint256 amt) external {
        (, int256 answer, , uint256 updatedAt, ) = oracle.latestRoundData();
        // BUG: no `require(block.timestamp - updatedAt < heartbeat)` — a stale
        // price is accepted at face value.
        updatedAt;
        token.transferFrom(msg.sender, address(this), amt);
        uint256 usdxOut = amt * uint256(answer) / 1e8;
        usdx.transfer(msg.sender, usdxOut);
    }
}

contract StaleSetup {
    MockERC20 public token;
    MockERC20 public usdx;
    MockAggregator public oracle;
    StaleVault public vault;
    address constant ATTACKER = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    constructor() {
        token = new MockERC20("Frozen Finance", "FRZ", 18);
        usdx = new MockERC20("USD X", "USDX", 18);
        oracle = new MockAggregator(8, 1, 1_000_000e8);

        vault = new StaleVault(token, usdx, oracle);
        usdx.mint(address(vault), 1_000_000 ether);     // 1M USDX in reserves

        // the feed is FROZEN at $100 from long ago; the market has since collapsed
        oracle.setAnswerStale(100e8, 1);                // updatedAt = 1 (ancient)

        // the attacker holds tokens that are really worthless but priced at $100
        token.mint(ATTACKER, 10_000 ether);             // 10k * $100 = $1M at the stale price
    }

    function isSolved() external view returns (bool) {
        return usdx.balanceOf(address(vault)) == 0;     // reserves drained
    }
}
