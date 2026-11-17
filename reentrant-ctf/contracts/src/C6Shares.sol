// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// C6 — The Shares.
/// ERC-4626 first-depositor share-inflation. The vault prices shares off its
/// raw asset balance, so the first depositor mints 1 share for 1 wei, *donates*
/// a large amount directly to the vault to inflate the share price, and the
/// next depositor's assets round down to ZERO shares — their deposit is then
/// redeemable by the attacker's single share. (ERC-4626 inflation class.)
///
/// Isolated training range. Do not deploy.

contract Asset {
    string public name = "Vault Asset";
    string public symbol = "AST";
    uint8 public decimals = 18;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function mint(address to, uint256 a) external { totalSupply += a; balanceOf[to] += a; }
    function approve(address s, uint256 a) external returns (bool) { allowance[msg.sender][s] = a; return true; }
    function transfer(address t, uint256 a) external returns (bool) { _x(msg.sender, t, a); return true; }
    function transferFrom(address f, address t, uint256 a) external returns (bool) {
        uint256 al = allowance[f][msg.sender];
        require(al >= a, "allowance");
        if (al != type(uint256).max) allowance[f][msg.sender] = al - a;
        _x(f, t, a);
        return true;
    }
    function _x(address f, address t, uint256 a) internal {
        require(balanceOf[f] >= a, "balance");
        balanceOf[f] -= a; balanceOf[t] += a;
    }
}

contract Vault4626 {
    Asset public asset;
    uint256 public totalShares;
    mapping(address => uint256) public shares;

    constructor(Asset a) { asset = a; }

    function deposit(uint256 assets) external returns (uint256 sharesOut) {
        uint256 supply = totalShares;
        uint256 bal = asset.balanceOf(address(this));
        // BUG: prices shares off the raw balance; no virtual shares/assets.
        sharesOut = supply == 0 ? assets : (assets * supply) / bal;
        shares[msg.sender] += sharesOut;          // a 0-share deposit is allowed
        totalShares += sharesOut;
        asset.transferFrom(msg.sender, address(this), assets);
    }

    function redeem(uint256 sh) external returns (uint256 assetsOut) {
        uint256 bal = asset.balanceOf(address(this));
        assetsOut = (sh * bal) / totalShares;
        shares[msg.sender] -= sh;
        totalShares -= sh;
        asset.transfer(msg.sender, assetsOut);
    }
}

contract SharesSetup {
    Asset public asset;
    Vault4626 public vault;
    address constant ATTACKER = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    constructor() {
        asset = new Asset();
        vault = new Vault4626(asset);
        asset.mint(ATTACKER, 10001 ether);          // attacker working capital
        asset.mint(address(this), 10000 ether);     // the "victim" deposit, held here
        asset.approve(address(vault), type(uint256).max);
    }

    /// the victim deposits — call this AFTER inflating the share price.
    function victimDeposit() external {
        vault.deposit(10000 ether);                 // rounds to 0 shares when inflated
    }

    function isSolved() external view returns (bool) {
        return vault.shares(address(this)) == 0           // victim got no shares
            && asset.balanceOf(address(this)) == 0        // victim lost its assets
            && asset.balanceOf(address(vault)) == 0;      // attacker drained the vault
    }
}
