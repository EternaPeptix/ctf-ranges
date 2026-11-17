// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "./Cheats.sol";
import "../src/C1Floor.sol";
import "../src/C2Stale.sol";
import "../src/C3Window.sol";
import "../src/C4Mirror.sol";
import "../src/C5Mint.sol";
import "../src/C6Scale.sol";

/// Deploys all six oracle challenges (funded) and writes their Setup addresses
/// to /shared/addrs.env for the dispenser and the solver.
contract Deploy is Script {
    function run() external {
        vm.startBroadcast();

        FloorSetup  s1 = new FloorSetup();
        StaleSetup  s2 = new StaleSetup();
        WindowSetup s3 = new WindowSetup();
        MirrorSetup s4 = new MirrorSetup{value: 1100 ether}();
        MintSetup   s5 = new MintSetup();
        ScaleSetup  s6 = new ScaleSetup();

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
