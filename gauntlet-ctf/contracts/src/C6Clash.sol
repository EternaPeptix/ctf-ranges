// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// C6 — The Clash.
/// A diamond-style router dispatches each call to a per-selector facet via
/// `delegatecall`. But facet registration has no access control. Register a
/// malicious facet for any selector; when it runs under the router's context it
/// can move the router's ETH. (EIP-2535 / proxy facet-registration misconfig.)
///
/// Isolated training range. Do not deploy.
contract Router {
    mapping(bytes4 => address) public facets;
    address public owner;

    constructor() payable { owner = msg.sender; }

    function setFacet(bytes4 sel, address facet) external {
        facets[sel] = facet;         // BUG: no onlyOwner
    }

    fallback() external payable {
        address f = facets[msg.sig];
        require(f != address(0), "no facet");
        assembly {
            calldatacopy(0, 0, calldatasize())
            let ok := delegatecall(gas(), f, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            if iszero(ok) { revert(0, returndatasize()) }
            return(0, returndatasize())
        }
    }

    receive() external payable {}
}

contract ClashSetup {
    Router public router;

    constructor() payable {
        router = new Router{value: msg.value}();
    }

    function isSolved() external view returns (bool) {
        return address(router).balance == 0;
    }
}
