// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {SignGuardRegistry} from "../src/SignGuardRegistry.sol";

contract SignGuardRegistryTest is Test {
    SignGuardRegistry reg;
    address attester = address(0xA11CE);
    address scam = address(0xBAD);
    address uniswap = address(0x0123);

    event Attested(
        bytes32 indexed intentHash,
        address indexed target,
        SignGuardRegistry.Verdict verdict,
        uint8 riskScore,
        bytes32 reportHash,
        address attester
    );

    function setUp() public {
        reg = new SignGuardRegistry(attester);
    }

    // ---------- atestado ----------

    function test_attestBlockUpdatesReputation() public {
        bytes32 h = keccak256("intent");
        vm.prank(attester);
        reg.attest(h, scam, SignGuardRegistry.Verdict.BLOCK, 90, keccak256("report"));

        SignGuardRegistry.Attestation memory a = reg.getAttestation(h);
        assertEq(a.intentHash, h);
        assertEq(a.target, scam);
        assertEq(uint8(a.verdict), uint8(SignGuardRegistry.Verdict.BLOCK));
        assertEq(a.riskScore, 90);
        assertEq(a.reportHash, keccak256("report"));
        assertEq(a.timestamp, block.timestamp);
        assertEq(a.attester, attester);
        assertTrue(reg.isBlocked(h));

        (uint32 total, uint32 blocks) = reg.reputation(scam);
        assertEq(total, 1);
        assertEq(blocks, 1);
    }

    function test_allowDoesNotCountAsBlock() public {
        bytes32 h = keccak256("swap");
        vm.prank(attester);
        reg.attest(h, uniswap, SignGuardRegistry.Verdict.ALLOW, 5, bytes32(0));

        assertFalse(reg.isBlocked(h));
        assertEq(reg.attestationCount(uniswap), 1);
        assertEq(reg.blockCount(uniswap), 0);
    }

    function test_emitsAttested() public {
        bytes32 h = keccak256("intent");
        vm.expectEmit(true, true, false, true);
        emit Attested(h, scam, SignGuardRegistry.Verdict.WARN, 50, bytes32(uint256(7)), attester);
        vm.prank(attester);
        reg.attest(h, scam, SignGuardRegistry.Verdict.WARN, 50, bytes32(uint256(7)));
    }

    function test_unknownIntentIsNotBlocked() public view {
        assertFalse(reg.isBlocked(keccak256("nunca atestado")));
        assertEq(reg.getAttestation(keccak256("nunca atestado")).timestamp, 0);
    }

    function test_reattestSameIntentDoesNotInflateReputation() public {
        bytes32 h = keccak256("intent");
        vm.startPrank(attester);
        reg.attest(h, scam, SignGuardRegistry.Verdict.BLOCK, 90, bytes32(0));
        reg.attest(h, scam, SignGuardRegistry.Verdict.BLOCK, 95, bytes32(0));
        vm.stopPrank();

        assertEq(reg.attestationCount(scam), 1);
        assertEq(reg.blockCount(scam), 1);
        assertEq(reg.getAttestation(h).riskScore, 95);
    }

    function test_reattestWithNewVerdictAdjustsBlockCount() public {
        bytes32 h = keccak256("intent");
        vm.startPrank(attester);
        reg.attest(h, scam, SignGuardRegistry.Verdict.BLOCK, 90, bytes32(0));
        reg.attest(h, scam, SignGuardRegistry.Verdict.WARN, 60, bytes32(0));
        vm.stopPrank();

        assertFalse(reg.isBlocked(h));
        assertEq(reg.attestationCount(scam), 1);
        assertEq(reg.blockCount(scam), 0);
    }

    function test_reattestWithNewTargetMovesReputation() public {
        bytes32 h = keccak256("intent");
        vm.startPrank(attester);
        reg.attest(h, uniswap, SignGuardRegistry.Verdict.BLOCK, 90, bytes32(0));
        reg.attest(h, scam, SignGuardRegistry.Verdict.BLOCK, 90, bytes32(0));
        vm.stopPrank();

        assertEq(reg.attestationCount(uniswap), 0);
        assertEq(reg.blockCount(uniswap), 0);
        assertEq(reg.attestationCount(scam), 1);
        assertEq(reg.blockCount(scam), 1);
    }

    // ---------- validações ----------

    function test_onlyAttesterCanAttest() public {
        vm.expectRevert(SignGuardRegistry.NotAttester.selector);
        reg.attest(bytes32(0), scam, SignGuardRegistry.Verdict.ALLOW, 0, bytes32(0));
    }

    function test_rejectsScoreAbove100() public {
        vm.prank(attester);
        vm.expectRevert(SignGuardRegistry.InvalidScore.selector);
        reg.attest(bytes32(0), scam, SignGuardRegistry.Verdict.WARN, 101, bytes32(0));
    }

    function testFuzz_scoreBounds(uint8 score) public {
        vm.prank(attester);
        if (score > 100) vm.expectRevert(SignGuardRegistry.InvalidScore.selector);
        reg.attest(keccak256("f"), scam, SignGuardRegistry.Verdict.WARN, score, bytes32(0));
    }

    // ---------- administração ----------

    function test_constructorRejectsZeroAttester() public {
        vm.expectRevert(SignGuardRegistry.ZeroAddress.selector);
        new SignGuardRegistry(address(0));
    }

    function test_ownerManagesAttesters() public {
        address bob = address(0xB0B);
        reg.setAttester(bob, true);
        assertTrue(reg.isAttester(bob));

        reg.setAttester(attester, false);
        vm.prank(attester);
        vm.expectRevert(SignGuardRegistry.NotAttester.selector);
        reg.attest(bytes32(0), scam, SignGuardRegistry.Verdict.ALLOW, 0, bytes32(0));
    }

    function test_onlyOwnerSetsAttester() public {
        vm.prank(attester);
        vm.expectRevert(SignGuardRegistry.NotOwner.selector);
        reg.setAttester(attester, false);
    }

    function test_transferOwnership() public {
        address newOwner = address(0xD0D0);
        reg.transferOwnership(newOwner);
        assertEq(reg.owner(), newOwner);

        vm.expectRevert(SignGuardRegistry.NotOwner.selector);
        reg.setAttester(address(0xB0B), true);

        vm.prank(newOwner);
        reg.setAttester(address(0xB0B), true);
        assertTrue(reg.isAttester(address(0xB0B)));
    }

    function test_transferOwnershipRejectsZero() public {
        vm.expectRevert(SignGuardRegistry.ZeroAddress.selector);
        reg.transferOwnership(address(0));
    }

    // ---------- hash ----------

    function testFuzz_intentHashMatchesAbiEncode(uint256 chainId, address from, address to, uint256 value, bytes calldata data)
        public
        view
    {
        bytes32 expected = keccak256(abi.encode(chainId, from, to, value, data));
        assertEq(reg.intentHash(chainId, from, to, value, data), expected);
    }
}
