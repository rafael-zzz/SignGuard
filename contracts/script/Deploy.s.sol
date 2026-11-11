// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {SignGuardRegistry} from "../src/SignGuardRegistry.sol";

/// forge script script/Deploy.s.sol --rpc-url $SEPOLIA_RPC_URL --private-key $ATTESTER_PRIVATE_KEY --broadcast
contract Deploy is Script {
    function run() external {
        vm.startBroadcast();
        SignGuardRegistry reg = new SignGuardRegistry(msg.sender);
        vm.stopBroadcast();
        console.log("SignGuardRegistry:", address(reg));
    }
}
