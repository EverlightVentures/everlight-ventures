const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with:", deployer.address);
  console.log("Balance:", hre.ethers.formatEther(await hre.ethers.provider.getBalance(deployer.address)), "ZIL");

  // 1. Deploy $BCRDI Token
  console.log("\n--- Deploying BCRDIToken ---");
  const BCRDIToken = await hre.ethers.getContractFactory("BCRDIToken");
  const bcrdi = await BCRDIToken.deploy(deployer.address); // team wallet = deployer for now
  await bcrdi.waitForDeployment();
  const bcrdiAddr = await bcrdi.getAddress();
  console.log("BCRDIToken:", bcrdiAddr);

  // 2. Deploy Card NFTs (ERC-1155)
  console.log("\n--- Deploying AlleyKingzCards ---");
  const Cards = await hre.ethers.getContractFactory("AlleyKingzCards");
  const cards = await Cards.deploy(
    "https://api.alleykingz.io/cards/{id}.json", // metadata URI
    deployer.address // royalty receiver
  );
  await cards.waitForDeployment();
  const cardsAddr = await cards.getAddress();
  console.log("AlleyKingzCards:", cardsAddr);

  // 3. Deploy Dog NFTs (ERC-721)
  console.log("\n--- Deploying AlleyKingzDogs ---");
  const Dogs = await hre.ethers.getContractFactory("AlleyKingzDogs");
  const dogs = await Dogs.deploy(
    "https://api.alleykingz.io/dogs/", // base URI
    deployer.address // royalty receiver
  );
  await dogs.waitForDeployment();
  const dogsAddr = await dogs.getAddress();
  console.log("AlleyKingzDogs:", dogsAddr);

  // 4. Deploy Staking
  console.log("\n--- Deploying BcrdiStaking ---");
  const Staking = await hre.ethers.getContractFactory("BcrdiStaking");
  const staking = await Staking.deploy(bcrdiAddr);
  await staking.waitForDeployment();
  const stakingAddr = await staking.getAddress();
  console.log("BcrdiStaking:", stakingAddr);

  // 5. Deploy Game Vault (P2E rewards)
  console.log("\n--- Deploying BcrdiGameVault ---");
  const Vault = await hre.ethers.getContractFactory("BcrdiGameVault");
  const vault = await Vault.deploy(bcrdiAddr);
  await vault.waitForDeployment();
  const vaultAddr = await vault.getAddress();
  console.log("BcrdiGameVault:", vaultAddr);

  // 6. Deploy Marketplace
  console.log("\n--- Deploying AlleyKingzMarketplace ---");
  const Marketplace = await hre.ethers.getContractFactory("AlleyKingzMarketplace");
  const marketplace = await Marketplace.deploy(
    bcrdiAddr,
    cardsAddr,
    dogsAddr,
    deployer.address // royalty receiver
  );
  await marketplace.waitForDeployment();
  const marketplaceAddr = await marketplace.getAddress();
  console.log("AlleyKingzMarketplace:", marketplaceAddr);

  // --- Post-Deploy Setup ---
  console.log("\n--- Post-Deploy Configuration ---");

  // Authorize game contracts on $BCRDI token
  await bcrdi.setGameContract(vaultAddr, true);
  console.log("GameVault authorized on BCRDI");

  // Authorize marketplace as minter on Cards (for future features)
  await cards.setAuthorizedMinter(vaultAddr, true);
  console.log("GameVault authorized as card minter");

  // Mint P2E allocation to GameVault (30M BCRDI)
  const p2eAmount = hre.ethers.parseEther("30000000");
  await bcrdi.mintToGameVault(vaultAddr, p2eAmount);
  console.log("30M BCRDI minted to GameVault");

  // Mint Staking allocation (15M BCRDI)
  const stakingAmount = hre.ethers.parseEther("15000000");
  await bcrdi.mintToStaking(stakingAddr, stakingAmount);
  console.log("15M BCRDI minted to Staking");

  // --- Register starter cards (18 core cards) ---
  console.log("\n--- Registering 18 Starter Cards ---");
  const starterCards = [
    // [name, rarity, type, elixirCost, breed]
    // Troops (type 0)
    ["Street Enforcer", 0, 0, 4, "Bulldog"],          // Common tank
    ["Sniper Coupe", 1, 0, 4, "Belgian Malinois"],    // Rare ranged DPS
    ["Pit Crew Pack", 0, 0, 3, "Chihuahua"],           // Common swarm
    ["Nitro Dragster", 1, 0, 4, "Greyhound"],          // Rare win-con
    ["Armored Semi", 3, 0, 8, "Cane Corso"],           // Legendary tank
    ["Ghost Interceptor", 2, 0, 3, "Doberman"],        // Epic assassin
    ["Shotgun Van", 1, 0, 4, "Rottweiler"],            // Rare splash
    ["Drone Swarm", 0, 0, 3, "Husky"],                 // Common air

    // Buildings (type 2)
    ["Roadside Turret", 1, 2, 3, "German Shepherd"],   // Rare defense
    ["Garage Bay", 1, 2, 5, "Pit Bull"],               // Rare spawner
    ["Railgun Emplacement", 2, 2, 6, "Great Dane"],    // Epic siege

    // Spells (type 1)
    ["EMP Pulse", 0, 1, 2, ""],                        // Common small spell
    ["Shockwave Ram", 0, 1, 2, ""],                    // Common knockback
    ["Molotov Barrage", 1, 1, 4, ""],                  // Rare DoT
    ["Airstrike", 2, 1, 6, ""],                        // Epic finisher
    ["Grapple Vortex", 2, 1, 3, ""],                   // Epic control
    ["Nitro Overdrive", 1, 1, 2, ""],                  // Rare utility
    ["Trunk Drop", 2, 1, 3, ""],                       // Epic bait
  ];

  // Register cards
  const cardNames = starterCards.map(c => c[0]);
  const rarities = starterCards.map(c => c[1]);
  const cardTypes = starterCards.map(c => c[2]);
  const elixirCosts = starterCards.map(c => c[3]);
  const breeds = starterCards.map(c => c[4]);
  const maxSupplies = starterCards.map(() => 0); // unlimited

  await cards.createCardBatch(cardNames, rarities, cardTypes, elixirCosts, breeds, maxSupplies);
  console.log(`${starterCards.length} starter cards registered`);

  // --- Summary ---
  console.log("\n========================================");
  console.log("ALLEY KINGZ DEPLOYMENT COMPLETE");
  console.log("========================================");
  console.log("BCRDIToken:          ", bcrdiAddr);
  console.log("AlleyKingzCards:     ", cardsAddr);
  console.log("AlleyKingzDogs:      ", dogsAddr);
  console.log("BcrdiStaking:        ", stakingAddr);
  console.log("BcrdiGameVault:      ", vaultAddr);
  console.log("AlleyKingzMarketplace:", marketplaceAddr);
  console.log("========================================");
  console.log("Starter cards:       ", starterCards.length);
  console.log("Dog breeds:           10 (Dogo Argentino is #1 Mythic)");
  console.log("P2E Pool:             30M BCRDI");
  console.log("Staking Pool:         15M BCRDI");
  console.log("========================================");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
