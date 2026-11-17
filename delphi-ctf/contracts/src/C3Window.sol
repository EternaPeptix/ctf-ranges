// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "./common/Mocks.sol";

/// C3 — The Window.
/// TWAP manipulation with too short an averaging window. A Uniswap-v2-style
/// cumulative-price oracle is read by a lending market. Pump the token's spot
/// price, hold it for the (short) window, and the time-weighted average the
/// market trusts is dragged up with it — so you borrow against collateral the
/// TWAP now massively over-values. (Inverse Finance.)
///
/// Isolated training range. Do not deploy.

/// Constant-product token<->USDX pool that accumulates a time-weighted price.
contract CumAMM {
    MockERC20 public token;
    MockERC20 public usdx;
    uint256 public priceCumulativeStored;   // sum of (USDX/token) * seconds
    uint256 public blockTimestampLast;

    constructor(MockERC20 t, MockERC20 u) {
        token = t; usdx = u; blockTimestampLast = block.timestamp;
    }

    function _reserves() internal view returns (uint256 tr, uint256 ur) {
        return (token.balanceOf(address(this)), usdx.balanceOf(address(this)));
    }

    /// spot USDX per token, 1e18
    function spot() public view returns (uint256) {
        (uint256 tr, uint256 ur) = _reserves();
        return tr == 0 ? 0 : ur * 1e18 / tr;
    }

    function priceCumulative() public view returns (uint256) {
        uint256 elapsed = block.timestamp - blockTimestampLast;
        return priceCumulativeStored + spot() * elapsed;
    }

    function _sync() internal {
        // accumulate the PRE-trade spot over the elapsed time, then checkpoint
        priceCumulativeStored = priceCumulative();
        blockTimestampLast = block.timestamp;
    }

    /// buy token with USDX (pushes the token's price up)
    function buyToken(uint256 usdxIn) external {
        _sync();
        (uint256 tr, uint256 ur) = _reserves();
        usdx.transferFrom(msg.sender, address(this), usdxIn);
        uint256 out = tr - (ur * tr) / (ur + usdxIn);
        token.transfer(msg.sender, out);
    }

    /// sell token for USDX (pushes the token's price down)
    function sellToken(uint256 tokIn) external {
        _sync();
        (uint256 tr, uint256 ur) = _reserves();
        token.transferFrom(msg.sender, address(this), tokIn);
        uint256 out = ur - (ur * tr) / (tr + tokIn);
        usdx.transfer(msg.sender, out);
    }
}

/// v2-style TWAP: averages the cumulative price over a fixed PERIOD.
contract TwapOracle {
    CumAMM public amm;
    uint256 public priceCumulativeLast;
    uint256 public timestampLast;
    uint256 public twap;                 // USDX per token, 1e18
    uint256 public constant PERIOD = 600;   // 10-minute window (too short)

    constructor(CumAMM a) { amm = a; }

    function update() external {
        uint256 cum = amm.priceCumulative();
        uint256 ts = block.timestamp;
        if (timestampLast == 0) {
            priceCumulativeLast = cum;
            timestampLast = ts;
            return;
        }
        uint256 elapsed = ts - timestampLast;
        if (elapsed >= PERIOD) {
            twap = (cum - priceCumulativeLast) / elapsed;
            priceCumulativeLast = cum;
            timestampLast = ts;
        }
    }
}

contract WindowLending {
    MockERC20 public token;
    MockERC20 public usdx;
    TwapOracle public oracle;
    mapping(address => uint256) public deposited;

    constructor(MockERC20 t, MockERC20 u, TwapOracle o) { token = t; usdx = u; oracle = o; }

    function deposit(uint256 amt) external {
        token.transferFrom(msg.sender, address(this), amt);
        deposited[msg.sender] += amt;
    }

    function borrow(uint256 usdxAmt) external {
        uint256 price = oracle.twap();                 // trusts the TWAP
        uint256 value = deposited[msg.sender] * price / 1e18;
        require(value >= usdxAmt, "undercollateralized");
        usdx.transfer(msg.sender, usdxAmt);
    }
}

contract WindowSetup {
    MockERC20 public token;
    MockERC20 public usdx;
    CumAMM public amm;
    TwapOracle public oracle;
    WindowLending public lending;
    address constant ATTACKER = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    constructor() {
        token = new MockERC20("Window Token", "WIN", 18);
        usdx = new MockERC20("USD X", "USDX", 18);

        // AMM seeded 1000 token / 1000 USDX  => spot 1 USDX/token
        amm = new CumAMM(token, usdx);
        token.mint(address(amm), 1000 ether);
        usdx.mint(address(amm), 1000 ether);

        oracle = new TwapOracle(amm);
        lending = new WindowLending(token, usdx, oracle);
        usdx.mint(address(lending), 50_000 ether);     // 50k USDX to lend

        // attacker: USDX to pump the pool, and tokens to pledge as collateral
        usdx.mint(ATTACKER, 10_000 ether);
        token.mint(ATTACKER, 1000 ether);
        // NOTE: the oracle is intentionally left un-checkpointed; the attacker
        // establishes the first checkpoint themselves (see the solver).
    }

    function isSolved() external view returns (bool) {
        return usdx.balanceOf(address(lending)) == 0;  // lending drained
    }
}
