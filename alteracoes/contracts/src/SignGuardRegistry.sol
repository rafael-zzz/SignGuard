// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title SignGuardRegistry
/// @notice Registro público e auditável dos vereditos do SignGuard.
///         O SignGuard NUNCA move fundos: só atesta. Quem assina continua sendo o dono da carteira.
/// @dev Dono: Davi.
contract SignGuardRegistry {
    enum Verdict { ALLOW, WARN, BLOCK }

    struct Attestation {
        bytes32 intentHash;   // keccak256(abi.encode(chainId, from, to, value, data))
        address target;       // contrato/endereço avaliado (spender, destinatário ou `to`)
        Verdict verdict;
        uint8 riskScore;      // 0-100
        bytes32 reportHash;   // keccak256 do relatório JSON canônico (fica off-chain)
        uint64 timestamp;
        address attester;
    }

    address public owner;
    mapping(address => bool) public isAttester;
    mapping(bytes32 => Attestation) private _attestations;
    /// @notice Reputação pública: quantas vezes um alvo recebeu BLOCK.
    mapping(address => uint32) public blockCount;
    mapping(address => uint32) public attestationCount;

    event Attested(
        bytes32 indexed intentHash, address indexed target, Verdict verdict, uint8 riskScore, bytes32 reportHash, address attester
    );
    event AttesterSet(address indexed attester, bool allowed);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    error NotOwner();
    error NotAttester();
    error InvalidScore();
    error ZeroAddress();

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    constructor(address firstAttester) {
        if (firstAttester == address(0)) revert ZeroAddress();
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
        isAttester[firstAttester] = true;
        emit AttesterSet(firstAttester, true);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    function setAttester(address who, bool allowed) external onlyOwner {
        if (who == address(0)) revert ZeroAddress();
        isAttester[who] = allowed;
        emit AttesterSet(who, allowed);
    }

    /// @notice Registra (ou atualiza) o veredito de uma intenção de transação.
    /// @dev Reatestar a mesma intenção substitui o registro sem inflar a reputação:
    ///      os contadores do registro anterior são desfeitos antes de aplicar o novo.
    function attest(bytes32 intentHash_, address target, Verdict verdict, uint8 riskScore, bytes32 reportHash) external {
        if (!isAttester[msg.sender]) revert NotAttester();
        if (riskScore > 100) revert InvalidScore();

        Attestation storage prev = _attestations[intentHash_];
        if (prev.timestamp != 0) {
            attestationCount[prev.target] -= 1;
            if (prev.verdict == Verdict.BLOCK) blockCount[prev.target] -= 1;
        }

        _attestations[intentHash_] = Attestation({
            intentHash: intentHash_,
            target: target,
            verdict: verdict,
            riskScore: riskScore,
            reportHash: reportHash,
            timestamp: uint64(block.timestamp),
            attester: msg.sender
        });
        attestationCount[target] += 1;
        if (verdict == Verdict.BLOCK) blockCount[target] += 1;
        emit Attested(intentHash_, target, verdict, riskScore, reportHash, msg.sender);
    }

    function getAttestation(bytes32 intentHash_) external view returns (Attestation memory) {
        return _attestations[intentHash_];
    }

    /// @notice Bloqueado? Usado por carteiras/guards (ex.: PolicyGuard, Safe Guard) para vetar a execução.
    function isBlocked(bytes32 intentHash_) external view returns (bool) {
        Attestation memory a = _attestations[intentHash_];
        return a.timestamp != 0 && a.verdict == Verdict.BLOCK;
    }

    /// @notice Reputação pública de um endereço numa chamada só (para front/carteiras).
    function reputation(address target) external view returns (uint32 attestations, uint32 blocks) {
        return (attestationCount[target], blockCount[target]);
    }

    /// @notice Mesmo cálculo feito no backend (tools/hashing.py).
    function intentHash(uint256 chainId, address from, address to, uint256 value, bytes calldata data)
        external
        pure
        returns (bytes32)
    {
        return keccak256(abi.encode(chainId, from, to, value, data));
    }
}
