// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// Minimal ERC20 for the challenges (configurable decimals).
contract MockERC20 {
    string public name;
    string public symbol;
    uint8 public decimals;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    constructor(string memory n, string memory s, uint8 d) {
        name = n; symbol = s; decimals = d;
    }
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

/// Minimal Chainlink-style aggregator. `minAnswer`/`maxAnswer` clamp the
/// reported answer (as real Chainlink feeds historically did); `setAnswerStale`
/// lets a Setup freeze `updatedAt` in the past.
contract MockAggregator {
    uint8 public decimals;
    int256 public minAnswer;
    int256 public maxAnswer;
    int256 internal _answer;
    uint256 internal _updatedAt;
    uint80 internal _roundId;

    constructor(uint8 d, int256 minA, int256 maxA) {
        decimals = d; minAnswer = minA; maxAnswer = maxA;
    }

    function setAnswer(int256 a) external {
        _answer = a; _updatedAt = block.timestamp; _roundId += 1;
    }
    function setAnswerStale(int256 a, uint256 updatedAt) external {
        _answer = a; _updatedAt = updatedAt; _roundId += 1;
    }

    function latestAnswer() public view returns (int256) {
        int256 a = _answer;
        if (a < minAnswer) a = minAnswer;      // the LUNA-style floor
        if (a > maxAnswer) a = maxAnswer;
        return a;
    }

    function latestRoundData()
        external view
        returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound)
    {
        return (_roundId, latestAnswer(), _updatedAt, _updatedAt, _roundId);
    }
}
