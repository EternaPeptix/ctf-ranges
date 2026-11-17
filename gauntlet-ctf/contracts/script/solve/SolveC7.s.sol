// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C7Keystone.sol";

/// Forge a "proof" from the generator alone: with the verifier checking only
/// e(A,VK)·e(C,VK) == 1, set C = -A (here A = G1 generator). By bilinearity the
/// product is e(A,VK)·e(A,VK)^-1 = 1, so the bogus proof verifies.
contract SolveC7 is Script {
    uint256 constant Q =
        21888242871839275222246405745257275088696311157297823662689037894645226208583;

    function run() external {
        KeystoneVault vault = KeystoneSetup(vm.envAddress("SETUP")).vault();
        Pairing.G1Point memory A = Pairing.G1Point(1, 2);        // G1 generator
        Pairing.G1Point memory C = Pairing.G1Point(1, Q - 2);    // -G1 generator
        vm.startBroadcast();
        vault.redeem(A, C);
        vm.stopBroadcast();
    }
}
