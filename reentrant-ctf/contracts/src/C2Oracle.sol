// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// C2 — The Oracle.
/// Spot-price oracle manipulation. A lending pool values token collateral using
/// the *instantaneous* reserves ratio of a tiny on-chain AMM. Dump tokens into
/// the AMM to crash the spot price, then borrow the pool dry for almost no
/// collateral. (bZx / Harvest / Mango class.)
///
/// Isolated training range. Do not deploy.

contract Token {
    string public name = "Puppet Token";
    string public symbol = "PUP";
    uint8 public decimals = 18;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function mint(address to, uint256 amt) external { totalSupply += amt; balanceOf[to] += amt; }
    function approve(address sp, uint256 amt) external returns (bool) { allowance[msg.sender][sp] = amt; return true; }
    function transfer(address to, uint256 amt) external returns (bool) { _xfer(msg.sender, to, amt); return true; }
    function transferFrom(address f, address t, uint256 amt) external returns (bool) {
        uint256 a = allowance[f][msg.sender];
        require(a >= amt, "allowance");
        if (a != type(uint256).max) allowance[f][msg.sender] = a - amt;
        _xfer(f, t, amt);
        return true;
    }
    function _xfer(address f, address t, uint256 amt) internal {
        require(balanceOf[f] >= amt, "balance");
        balanceOf[f] -= amt; balanceOf[t] += amt;
    }
}

/// Minimal constant-product ETH<->Token pool, doubling as the price oracle.
contract AMM {
    Token public token;
    constructor(Token t) payable { token = t; }

    /// spot price: ETH per token, scaled by 1e18.
    function priceTokenInEth() public view returns (uint256) {
        uint256 tbal = token.balanceOf(address(this));
        require(tbal > 0, "no liquidity");
        return address(this).balance * 1e18 / tbal;
    }

    /// sell `amt` tokens into the pool for ETH (x*y=k).
    function sellToken(uint256 amt) external {
        uint256 tbal = token.balanceOf(address(this));
        uint256 ebal = address(this).balance;
        token.transferFrom(msg.sender, address(this), amt);
        uint256 out = ebal - (ebal * tbal) / (tbal + amt);
        (bool ok, ) = msg.sender.call{value: out}("");
        require(ok, "eth out");
    }

    receive() external payable {}
}

/// Lending pool that trusts the AMM spot price to value collateral (the bug).
contract LendingPool {
    Token public token;
    AMM public amm;
    constructor(Token t, AMM a) { token = t; amm = a; }

    /// borrow `amount` tokens; requires ETH collateral worth 2x the tokens
    /// at the AMM spot price.
    function borrow(uint256 amount) external payable {
        uint256 price = amm.priceTokenInEth();              // ETH per token (1e18)
        uint256 required = amount * price * 2 / 1e18;        // 200% collateral
        require(msg.value >= required, "insufficient collateral");
        token.transfer(msg.sender, amount);
    }

    receive() external payable {}
}

contract OracleSetup {
    Token public token;
    AMM public amm;
    LendingPool public pool;
    address constant ATTACKER = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

    constructor() payable {
        token = new Token();
        // AMM: 10 ETH + 10 token  => spot price 1 ETH/token
        amm = new AMM{value: msg.value}(token);
        token.mint(address(amm), 10 ether);
        // the lending pool holds 100 token to lend out
        pool = new LendingPool(token, amm);
        token.mint(address(pool), 100 ether);
        // the attacker is seeded with enough tokens to swamp the tiny AMM
        token.mint(ATTACKER, 1000 ether);
    }

    function isSolved() external view returns (bool) {
        return token.balanceOf(address(pool)) == 0;         // pool drained
    }
}
