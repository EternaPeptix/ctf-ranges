// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C1Signet.sol";

/// Recover the signer's private key from the two nonce-reusing signatures,
/// forge a withdraw authorization, and drain.
contract SolveC1 is Script {
    uint256 constant N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141;
    address constant ME = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    function run() external {
        SignetVault vault = SignetSetup(vm.envAddress("SETUP")).vault();
        uint256 r = vault.R();
        uint256 s1 = vault.S1();
        uint256 h1 = vault.H1();
        uint256 s2 = vault.S2();
        uint256 h2 = vault.H2();

        // k = (h1 - h2) / (s1 - s2);   d = (s1*k - h1) / r    (mod n)
        uint256 k = mulmod(_sub(h1, h2), _inv(_sub(s1, s2)), N);
        uint256 d = mulmod(_sub(mulmod(s1, k, N), h1), _inv(r), N);

        (uint8 v, bytes32 rr, bytes32 ss) = vm.sign(d, vault.WITHDRAW_DIGEST());
        vm.startBroadcast();
        vault.withdraw(ME, v, rr, ss);
        vm.stopBroadcast();
    }

    function _sub(uint256 a, uint256 b) internal pure returns (uint256) {
        return addmod(a % N, N - (b % N), N);
    }
    function _inv(uint256 a) internal view returns (uint256) {
        return _modexp(a, N - 2, N);     // Fermat's little theorem
    }
    function _modexp(uint256 base, uint256 e, uint256 m) internal view returns (uint256 out) {
        assembly {
            let p := mload(0x40)
            mstore(p, 0x20) mstore(add(p, 0x20), 0x20) mstore(add(p, 0x40), 0x20)
            mstore(add(p, 0x60), base) mstore(add(p, 0x80), e) mstore(add(p, 0xa0), m)
            if iszero(staticcall(gas(), 0x05, p, 0xc0, p, 0x20)) { revert(0, 0) }
            out := mload(p)
        }
    }
}
