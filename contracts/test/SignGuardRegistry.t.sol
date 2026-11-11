// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {SignGuardRegistry} from "../src/SignGuardRegistry.sol";

contract SignGuardRegistryTest is Test {
    SignGuardRegistry reg;
    address attester = address(0xA11CE);
    address scam = address(0xBAD);

    function setUp() public {
        reg = new SignGuardRegistry(attester);
    }

    function test_attestBlockUpdatesReputation() public {
        bytes32 h = keccak256("intent");
        vm.prank(attester);
        reg.attest(h, scam, SignGuardRegistry.Verdict.BLOCK, 90, keccak256("report"));

        SignGuardRegistry.Attestation memory a = reg.getAttestation(h);
        assertEq(a.target, scam);
        assertEq(a.riskScore, 90);
        assertTrue(reg.isBlocked(h));
        assertEq(reg.blockCount(scam), 1);
    }

    function test_onlyAttesterCanAttest() public {
        vm.expectRevert(SignGuardRegistry.NotAttester.selector);
        reg.attest(bytes32(0), scam, SignGuardRegistry.Verdict.ALLOW, 0, bytes32(0));
    }

    function test_rejectsScoreAbove100() public {
        vm.prank(attester);
        vm.expectRevert(SignGuardRegistry.InvalidScore.selector);
        reg.attest(bytes32(0), scam, SignGuardRegistry.Verdict.WARN, 101, bytes32(0));
    }

    function test_intentHashMatchesBackend() public view {
        bytes memory data = hex"a9059cbb";
        bytes32 expected = keccak256(abi.encode(uint256(1), address(1), address(2), uint256(0), data));
        assertEq(reg.intentHash(1, address(1), address(2), 0, data), expected);
    }
}
