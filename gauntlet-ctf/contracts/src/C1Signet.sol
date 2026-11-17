// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// C1 — The Signet.
/// ECDSA nonce reuse. The vault's authorizer once signed two different messages
/// with the SAME nonce k — so both leaked signatures share the same `r`. From
/// (r, s1, h1) and (r, s2, h2) the private key falls out by modular arithmetic:
///   k = (h1 - h2) / (s1 - s2),   d = (s1·k - h1) / r   (mod n).
/// Recover d, forge a signature over the withdraw digest, and drain.
///
/// Isolated training range. Do not deploy.
contract SignetVault {
    address public immutable signer;
    bytes32 public constant WITHDRAW_DIGEST = keccak256("GAUNTLET_SIGNET_WITHDRAW");

    // Two leaked signatures from `signer` (note: identical r => reused nonce).
    uint256 public constant R  = 0xb717cf59ca3dbf7d9a4d0d258d80f9e533648549c35476fe0fc97b42e519c8e0;
    uint256 public constant S1 = 0x878dfb76699a6e5aa587f135b9679ac0c62c1c1a5390a8f374e55119643e6f3d;
    uint256 public constant H1 = 0x1111111111111111111111111111111111111111111111111111111111111111;
    uint256 public constant S2 = 0xcd466c015fc00bd34ab6464de5d922cfab58bd8ed7ae74ee9df7cd93a40b5c3e;
    uint256 public constant H2 = 0x2222222222222222222222222222222222222222222222222222222222222222;

    constructor(address _signer) payable { signer = _signer; }

    function withdraw(address to, uint8 v, bytes32 r, bytes32 s) external {
        require(ecrecover(WITHDRAW_DIGEST, v, r, s) == signer, "bad signature");
        (bool ok, ) = to.call{value: address(this).balance}("");
        require(ok, "transfer failed");
    }
}

contract SignetSetup {
    SignetVault public vault;

    constructor() payable {
        // signer address derived from the private key the two leaked sigs expose
        vault = new SignetVault{value: msg.value}(0x97b9210c81f67a7FCC3811552BcBB0ECc18ad347);
    }

    function isSolved() external view returns (bool) {
        return address(vault).balance == 0;
    }
}
