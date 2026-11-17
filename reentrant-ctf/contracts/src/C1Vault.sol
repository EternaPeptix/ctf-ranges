// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// C1 — The Vault.
/// Classic reentrancy: a Checks-Effects-Interactions violation. withdraw()
/// sends ETH to the caller *before* zeroing their balance, so a malicious
/// receiver re-enters withdraw() and drains everyone's funds. (The DAO, 2016.)
///
/// Isolated training range. Do not deploy.
contract Vault {
    mapping(address => uint256) public balanceOf;

    function deposit() external payable {
        balanceOf[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 amount = balanceOf[msg.sender];
        require(amount > 0, "nothing to withdraw");
        (bool ok, ) = msg.sender.call{value: amount}("");   // interaction FIRST
        require(ok, "transfer failed");
        balanceOf[msg.sender] = 0;                           // effect too late
    }

    receive() external payable {}
}

contract VaultSetup {
    Vault public vault;

    constructor() payable {
        vault = new Vault();
        // other customers' deposits — the pooled funds an attacker will steal
        vault.deposit{value: msg.value}();
    }

    function isSolved() external view returns (bool) {
        return address(vault).balance == 0;
    }
}
