// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// C2 — The Branch.
/// Merkle second-preimage. The airdrop's leaves are `keccak256(a, b)` with two
/// 32-byte fields — exactly the same preimage shape as an internal node
/// `keccak256(left, right)`. So an INTERNAL NODE can be passed off as a leaf:
/// present (a, b) = (childLeafL, childLeafR), and `keccak256(a, b)` equals a real
/// node in the tree. The payout is `uint256(b)` — i.e. a child leaf hash — an
/// astronomical number that drains the airdrop. (OpenZeppelin's 64-byte-leaf
/// warning.)
///
/// Isolated training range. Do not deploy.
contract AirdropVault {
    bytes32 public root;
    bytes32[4] public legitLeaves;              // published allowlist leaves
    mapping(bytes32 => bool) public claimed;

    constructor(address[4] memory members, uint256[4] memory amounts) payable {
        bytes32[4] memory l;
        for (uint256 i = 0; i < 4; i++) {
            l[i] = keccak256(abi.encodePacked(bytes32(uint256(uint160(members[i]))), bytes32(amounts[i])));
            legitLeaves[i] = l[i];
        }
        bytes32 p01 = keccak256(abi.encodePacked(l[0], l[1]));
        bytes32 p23 = keccak256(abi.encodePacked(l[2], l[3]));
        root = keccak256(abi.encodePacked(p01, p23));
    }

    function _verify(bytes32 leaf, bytes32[] calldata proof) internal view returns (bool) {
        bytes32 h = leaf;
        for (uint256 i = 0; i < proof.length; i++) {
            h = keccak256(abi.encodePacked(h, proof[i]));   // fixed order, no leaf/node domain split
        }
        return h == root;
    }

    function claim(bytes32 a, bytes32 b, bytes32[] calldata proof) external {
        bytes32 leaf = keccak256(abi.encodePacked(a, b));
        require(_verify(leaf, proof), "bad proof");
        require(!claimed[leaf], "already claimed");
        claimed[leaf] = true;
        uint256 amount = uint256(b);
        uint256 pay = amount > address(this).balance ? address(this).balance : amount;
        (bool ok, ) = msg.sender.call{value: pay}("");
        require(ok, "pay failed");
    }

    function leaves() external view returns (bytes32[4] memory) { return legitLeaves; }
}

contract BranchSetup {
    AirdropVault public vault;

    constructor() payable {
        address[4] memory m = [
            0x1111111111111111111111111111111111111111,
            0x2222222222222222222222222222222222222222,
            0x3333333333333333333333333333333333333333,
            0x4444444444444444444444444444444444444444
        ];
        uint256[4] memory a = [uint256(1 ether), 2 ether, 3 ether, 4 ether];
        vault = new AirdropVault{value: msg.value}(m, a);
    }

    function isSolved() external view returns (bool) {
        return address(vault).balance == 0;
    }
}
