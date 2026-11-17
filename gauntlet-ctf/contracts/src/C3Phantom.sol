// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// C3 — The Phantom.
/// `ecrecover` returns `address(0)` for a malformed signature. The vault's
/// recovery guardian was never initialized, so it is also `address(0)`. Submit
/// any invalid signature and `ecrecover(...) == recoveryGuardian` holds — you
/// pass the guardian check with garbage and drain.
///
/// Isolated training range. Do not deploy.
contract GuardedVault {
    address public recoveryGuardian;   // left uninitialized => address(0)
    bytes32 public constant ACTION = keccak256("GAUNTLET_EMERGENCY_WITHDRAW");

    constructor() payable {}

    function emergencyWithdraw(address to, uint8 v, bytes32 r, bytes32 s) external {
        // BUG: recoveryGuardian is address(0), and ecrecover() yields address(0)
        // for an invalid signature, so this check passes with junk inputs.
        require(ecrecover(ACTION, v, r, s) == recoveryGuardian, "not guardian");
        (bool ok, ) = to.call{value: address(this).balance}("");
        require(ok, "transfer failed");
    }
}

contract PhantomSetup {
    GuardedVault public vault;

    constructor() payable {
        vault = new GuardedVault{value: msg.value}();
    }

    function isSolved() external view returns (bool) {
        return address(vault).balance == 0;
    }
}
