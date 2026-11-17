// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// C4 — The Permit.
/// Signature replay: a signed payout voucher whose digest binds only
/// (recipient, amount) — no nonce, no deadline, and nothing marks a voucher as
/// used. One legitimately-signed voucher can therefore be replayed until the
/// contract is drained. (permit / meta-tx replay class.)
///
/// Isolated training range. Do not deploy.
contract Payments {
    address public signer;

    constructor(address _signer) payable { signer = _signer; }

    function claim(address to, uint256 amount, uint8 v, bytes32 r, bytes32 s) external {
        bytes32 h = keccak256(abi.encodePacked(to, amount));
        bytes32 digest = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", h));
        require(ecrecover(digest, v, r, s) == signer, "bad signature");
        // BUG: no nonce / no replay guard — the same voucher claims forever
        (bool ok, ) = to.call{value: amount}("");
        require(ok, "pay failed");
    }

    receive() external payable {}
}

contract PaymentsSetup {
    Payments public payments;
    address public voucherTo;
    uint256 public voucherAmount;
    uint8 public sigV;
    bytes32 public sigR;
    bytes32 public sigS;

    constructor(address _signer, address _to, uint256 _amount, uint8 v, bytes32 r, bytes32 s)
        payable
    {
        payments = new Payments{value: msg.value}(_signer);
        voucherTo = _to;
        voucherAmount = _amount;
        sigV = v; sigR = r; sigS = s;
    }

    function isSolved() external view returns (bool) {
        return address(payments).balance == 0;
    }
}
