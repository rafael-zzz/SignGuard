// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {SignGuardRegistry} from "../src/SignGuardRegistry.sol";

/// Deploy na Sepolia (rodar de dentro de contracts/, com o .env da raiz carregado):
///   set -a && source <(tr -d '\r' < ../.env) && set +a   # exporta as variáveis e remove \r do Windows
///   forge script script/Deploy.s.sol --rpc-url $SEPOLIA_RPC_URL --broadcast --gas-estimate-multiplier 800
///
/// O multiplicador é necessário: a Sepolia cobra bem mais gas para criar contrato do que a simulação
/// local do forge 1.5 calcula (~1,9M simulado vs ~10M estimado pelo nó). Sem ele, o deploy fica sem gas.
///
/// - ATTESTER_PRIVATE_KEY (obrigatório, com 0x): paga o deploy e vira owner.
/// - ATTESTER_ADDRESS (opcional): carteira autorizada a atestar; padrão = a mesma do deploy.
contract Deploy is Script {
    function run() external returns (SignGuardRegistry reg) {
        uint256 pk = vm.envUint("ATTESTER_PRIVATE_KEY");
        address deployer = vm.addr(pk);
        address attester = vm.envOr("ATTESTER_ADDRESS", deployer);

        vm.startBroadcast(pk);
        reg = new SignGuardRegistry(attester);
        vm.stopBroadcast();

        console.log("Owner:   ", deployer);
        console.log("Attester:", attester);
        console.log("Cole no .env -> REGISTRY_ADDRESS=", address(reg));
    }
}
