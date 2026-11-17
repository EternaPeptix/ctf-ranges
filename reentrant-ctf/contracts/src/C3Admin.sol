// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// C3 — The Admin.
/// Broken access control: the treasury's initializer was left unprotected
/// (no "already initialized" guard), so anyone can re-initialize it, become
/// owner, and sweep the funds. (Parity-init / Rubixi class.)
///
/// Isolated training range. Do not deploy.
contract Treasury {
    address public owner;

    function initialize(address _owner) external {
        owner = _owner;              // BUG: callable again by anyone
    }

    function sweep(address payable to) external {
        require(msg.sender == owner, "not owner");
        to.transfer(address(this).balance);
    }

    receive() external payable {}
}

contract TreasurySetup {
    Treasury public treasury;

    constructor() payable {
        treasury = new Treasury();
        treasury.initialize(address(this));                 // "properly" initialized
        (bool ok, ) = address(treasury).call{value: msg.value}("");
        require(ok, "fund");
    }

    function isSolved() external view returns (bool) {
        return address(treasury).balance == 0;
    }
}
