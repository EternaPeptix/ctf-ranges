// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// C5 — The Dice.
/// Weak on-chain randomness. The "provably fair" game derives its roll from
/// `block.prevrandao`, which is constant within a block and readable by any
/// contract in the same transaction. Compute the roll yourself and bet it.
///
/// Isolated training range. Do not deploy.
contract Casino {
    constructor() payable {}

    function roll(uint256 guess) external {
        uint256 r = uint256(keccak256(abi.encodePacked(block.prevrandao))) % 6 + 1;
        require(guess == r, "you lose");
        (bool ok, ) = msg.sender.call{value: address(this).balance}("");
        require(ok, "payout failed");
    }
}

contract DiceSetup {
    Casino public casino;

    constructor() payable {
        casino = new Casino{value: msg.value}();
    }

    function isSolved() external view returns (bool) {
        return address(casino).balance == 0;
    }
}
