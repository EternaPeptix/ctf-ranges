// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// C4 — The Latch.
/// EIP-1153 transient-storage reentrancy. The bank guards against reentrancy
/// with a modern `tstore`/`tload` lock — but keys the lock by `msg.sig`, i.e.
/// PER FUNCTION. Two functions pay out the same balance, each with its own
/// (per-selector) lock, so re-entering the *other* one from the ETH callback is
/// not blocked: classic cross-function reentrancy, past a shiny new lock.
///
/// Isolated training range (requires the Cancun hardfork for tstore/tload).
/// Do not deploy.
contract Bank {
    mapping(address => uint256) public balanceOf;

    modifier lock() {
        bytes32 slot = bytes32(msg.sig);          // BUG: per-selector key
        assembly {
            if tload(slot) { revert(0, 0) }
            tstore(slot, 1)
        }
        _;
        assembly { tstore(slot, 0) }
    }

    function deposit() external payable {
        balanceOf[msg.sender] += msg.value;
    }

    function withdraw() external lock {
        uint256 amount = balanceOf[msg.sender];
        (bool ok, ) = msg.sender.call{value: amount}("");   // interaction first
        require(ok, "transfer failed");
        balanceOf[msg.sender] = 0;
    }

    // same payout logic, DIFFERENT selector => a different transient lock
    function emergencyWithdraw() external lock {
        uint256 amount = balanceOf[msg.sender];
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
        balanceOf[msg.sender] = 0;
    }
}

contract LatchSetup {
    Bank public bank;

    constructor() payable {
        bank = new Bank();
        bank.deposit{value: msg.value}();   // other customers' pooled funds
    }

    function isSolved() external view returns (bool) {
        return address(bank).balance == 0;
    }
}
