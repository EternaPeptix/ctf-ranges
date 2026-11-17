// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "./Cheats.sol";
import "../src/C1Vault.sol";
import "../src/C2Oracle.sol";
import "../src/C3Admin.sol";
import "../src/C4Permit.sol";
import "../src/C5Upgrade.sol";
import "../src/C6Shares.sol";

/// Deploys all six challenges (funded) and writes their Setup addresses to
/// /shared/addrs.env for the dispenser and the solver.
contract Deploy is Script {
    address constant ATTACKER = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;
    // organizer-side signing key for the C4 voucher (the attacker never sees it)
    uint256 constant SIGNER_PK =
        0x515170000000000000000000000000000000000000000000000000000000c0de;

    function run() external {
        vm.startBroadcast();

        VaultSetup s1 = new VaultSetup{value: 5 ether}();
        OracleSetup s2 = new OracleSetup{value: 10 ether}();
        TreasurySetup s3 = new TreasurySetup{value: 10 ether}();

        // C4: sign ONE legitimate voucher (attacker, 1 ETH); replay drains it.
        address signer = vm.addr(SIGNER_PK);
        bytes32 h = keccak256(abi.encodePacked(ATTACKER, uint256(1 ether)));
        bytes32 digest = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", h));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(SIGNER_PK, digest);
        PaymentsSetup s4 = new PaymentsSetup{value: 10 ether}(signer, ATTACKER, 1 ether, v, r, s);

        ProxySetup s5 = new ProxySetup{value: 10 ether}();
        SharesSetup s6 = new SharesSetup();

        vm.stopBroadcast();

        string memory out = string.concat(
            "C1_SETUP=", vm.toString(address(s1)), "\n",
            "C2_SETUP=", vm.toString(address(s2)), "\n",
            "C3_SETUP=", vm.toString(address(s3)), "\n",
            "C4_SETUP=", vm.toString(address(s4)), "\n",
            "C5_SETUP=", vm.toString(address(s5)), "\n",
            "C6_SETUP=", vm.toString(address(s6)), "\n"
        );
        vm.writeFile("/shared/addrs.env", out);
    }
}
