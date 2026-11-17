// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// C5 — The Upgrade.
/// Proxy storage collision via delegatecall. The proxy's storage layout
/// (slot0 = implementation, slot1 = owner) collides with the logic contract's
/// layout (slot0 = pending, slot1 = nominee). A benign-looking logic call that
/// writes slot1 therefore overwrites the proxy's `owner`; the attacker then
/// sweeps the proxy. (Parity multisig, 2017.)
///
/// Isolated training range. Do not deploy.
contract WalletProxy {
    address public implementation;   // slot 0
    address public owner;            // slot 1

    constructor(address impl, address _owner) payable {
        implementation = impl;
        owner = _owner;
    }

    function sweep(address payable to) external {
        require(msg.sender == owner, "not owner");
        to.transfer(address(this).balance);
    }

    fallback() external payable {
        (bool ok, ) = implementation.delegatecall(msg.data);
        require(ok, "delegatecall failed");
    }

    receive() external payable {}
}

contract WalletLogic {
    address public pending;    // slot 0  (collides with proxy.implementation)
    address public nominee;    // slot 1  (collides with proxy.owner)

    function nominate(address who) external {
        nominee = who;         // via delegatecall this writes proxy.owner
    }
}

contract ProxySetup {
    WalletProxy public proxyWallet;
    WalletLogic public logic;

    constructor() payable {
        logic = new WalletLogic();
        proxyWallet = new WalletProxy{value: msg.value}(address(logic), address(this));
    }

    function isSolved() external view returns (bool) {
        return address(proxyWallet).balance == 0;
    }
}
