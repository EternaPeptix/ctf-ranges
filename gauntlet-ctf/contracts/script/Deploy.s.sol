// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "./Cheats.sol";
import "../src/C1Signet.sol";
import "../src/C2Branch.sol";
import "../src/C3Phantom.sol";
import "../src/C4Latch.sol";
import "../src/C5Dice.sol";
import "../src/C6Clash.sol";
import "../src/C7Keystone.sol";

/// Deploys all seven challenges (funded) and writes their Setup addresses to
/// /shared/addrs.env for the dispenser and the solver.
contract Deploy is Script {
    function run() external {
        vm.startBroadcast();

        SignetSetup   s1 = new SignetSetup{value: 10 ether}();
        BranchSetup   s2 = new BranchSetup{value: 100 ether}();
        PhantomSetup  s3 = new PhantomSetup{value: 10 ether}();
        LatchSetup    s4 = new LatchSetup{value: 100 ether}();
        DiceSetup     s5 = new DiceSetup{value: 10 ether}();
        ClashSetup    s6 = new ClashSetup{value: 10 ether}();
        KeystoneSetup s7 = new KeystoneSetup{value: 10 ether}();

        vm.stopBroadcast();

        string memory out = string.concat(
            "C1_SETUP=", vm.toString(address(s1)), "\n",
            "C2_SETUP=", vm.toString(address(s2)), "\n",
            "C3_SETUP=", vm.toString(address(s3)), "\n",
            "C4_SETUP=", vm.toString(address(s4)), "\n",
            "C5_SETUP=", vm.toString(address(s5)), "\n",
            "C6_SETUP=", vm.toString(address(s6)), "\n",
            "C7_SETUP=", vm.toString(address(s7)), "\n"
        );
        vm.writeFile("/shared/addrs.env", out);
    }
}
