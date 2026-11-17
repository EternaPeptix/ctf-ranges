// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// C7 — The Keystone (capstone).
/// A BN254 pairing-based "proof" verifier with a fatal soundness gap. It checks
///   e(A, VK) · e(C, VK) == 1
/// but never binds A and C to a public statement, and never checks they are
/// non-trivial group elements. By bilinearity that equation holds for ANY A with
/// C = -A (or A = C = O), so a valid-looking "proof" can be forged from the
/// generator alone — no witness, no trusted setup secret. Forge it and drain.
///
/// Isolated training range. Do not deploy.

library Pairing {
    struct G1Point { uint256 X; uint256 Y; }
    struct G2Point { uint256[2] X; uint256[2] Y; }

    uint256 constant Q =
        21888242871839275222246405745257275088696311157297823662689037894645226208583;

    function P1() internal pure returns (G1Point memory) { return G1Point(1, 2); }

    /// the BN254 G2 generator (canonical encoding for precompile 0x08)
    function P2() internal pure returns (G2Point memory) {
        return G2Point(
            [11559732032986387107991004021392285783925812861821192530917403151452391805634,
             10857046999023057135944570762232829481370756359578518086990519993285655852781],
            [4082367875863433681332203403145435568316851327593401208105741076214120093531,
             8495653923123431417604973247489272438418190587263600148770280649306958101930]
        );
    }

    function negate(G1Point memory p) internal pure returns (G1Point memory) {
        if (p.X == 0 && p.Y == 0) return G1Point(0, 0);
        return G1Point(p.X, Q - (p.Y % Q));
    }

    function pairing(G1Point[] memory p1, G2Point[] memory p2) internal view returns (bool) {
        require(p1.length == p2.length, "len");
        uint256 elements = p1.length;
        uint256 inputSize = elements * 6;
        uint256[] memory input = new uint256[](inputSize);
        for (uint256 i = 0; i < elements; i++) {
            input[i * 6 + 0] = p1[i].X;
            input[i * 6 + 1] = p1[i].Y;
            input[i * 6 + 2] = p2[i].X[0];
            input[i * 6 + 3] = p2[i].X[1];
            input[i * 6 + 4] = p2[i].Y[0];
            input[i * 6 + 5] = p2[i].Y[1];
        }
        uint256[1] memory out;
        bool success;
        assembly {
            success := staticcall(gas(), 8, add(input, 0x20), mul(inputSize, 0x20), out, 0x20)
        }
        require(success, "pairing-failed");
        return out[0] != 0;
    }

    function pairingProd2(G1Point memory a1, G2Point memory a2, G1Point memory b1, G2Point memory b2)
        internal view returns (bool)
    {
        G1Point[] memory p1 = new G1Point[](2);
        G2Point[] memory p2 = new G2Point[](2);
        p1[0] = a1; p1[1] = b1;
        p2[0] = a2; p2[1] = b2;
        return pairing(p1, p2);
    }
}

contract ProofVerifier {
    Pairing.G2Point VK;

    constructor() { VK = Pairing.P2(); }

    function verify(Pairing.G1Point memory A, Pairing.G1Point memory C) public view returns (bool) {
        // BUG: under-constrained — accepts any A, C with e(A,VK)·e(C,VK) == 1.
        return Pairing.pairingProd2(A, VK, C, VK);
    }
}

contract KeystoneVault {
    ProofVerifier public verifier;

    constructor() payable { verifier = new ProofVerifier(); }

    function redeem(Pairing.G1Point memory A, Pairing.G1Point memory C) external {
        require(verifier.verify(A, C), "invalid proof");
        (bool ok, ) = msg.sender.call{value: address(this).balance}("");
        require(ok, "transfer failed");
    }
}

contract KeystoneSetup {
    KeystoneVault public vault;

    constructor() payable {
        vault = new KeystoneVault{value: msg.value}();
    }

    function isSolved() external view returns (bool) {
        return address(vault).balance == 0;
    }
}
