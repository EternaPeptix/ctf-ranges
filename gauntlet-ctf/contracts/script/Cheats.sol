// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// Minimal vendored Foundry cheatcode interface + Script base (no forge-std).
interface Vm {
    function startBroadcast() external;
    function stopBroadcast() external;
    function sign(uint256 privateKey, bytes32 digest)
        external pure returns (uint8 v, bytes32 r, bytes32 s);
    function addr(uint256 privateKey) external pure returns (address);
    function envAddress(string calldata name) external view returns (address);
    function writeFile(string calldata path, string calldata data) external;
    function toString(address value) external pure returns (string memory);
}

abstract contract Script {
    Vm internal constant vm = Vm(0x7109709ECfa91a80626fF3989D68f67F5b1DD12D);
}
