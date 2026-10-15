// Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
// Brute: impact effects (shockwave ring, debris, crater, ground cracks, clap cone) and the physics car a lifted / knocked traffic car
// turns into. Everything is built from engine shapes + /Game/Traversal/Materials/M_TravColor MIDs so it needs no new assets.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Life/WHLifeTraffic.h"
#include "BruteFx.generated.h"

class UStaticMeshComponent;
class UBoxComponent;
class UMaterialInstanceDynamic;
class UStaticMesh;

namespace BruteFx
{
	UMaterialInstanceDynamic* Mat(UObject* Outer, const FLinearColor& C, float Emissive = 0.f);
	UStaticMesh* Cube();
	UStaticMesh* Sphere();
	UStaticMesh* Cylinder();
}

/** One impact: an expanding dust ring, flying debris chunks, a crater disk with radial cracks (persists), or a forward clap cone. */
UCLASS()
class WEBHOMAGE_API ABruteShockwave : public AActor
{
	GENERATED_BODY()
public:
	ABruteShockwave();
	/** RadiusM: ring reach. bCrater: leave a crater + cracks. ConeDir non-zero: a forward cone (thunderclap) instead of a full ring. */
	void Init(float RadiusM, bool bCrater, const FVector& ConeDir = FVector::ZeroVector, float Strength = 1.f);
	virtual void Tick(float Dt) override;

private:
	struct FPart { TObjectPtr<UStaticMeshComponent> C; FVector P, V, S0; float Life = 1.f, Age = 0.f, Spin = 0.f; uint8 Kind = 0; bool bRest = false; };
	TArray<FPart> Parts;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Comps;
	float Age = 0.f, Radius = 8.f, CraterLife = 30.f;
	bool bHasCrater = false;
	UStaticMeshComponent* Add(UStaticMesh* M, UMaterialInstanceDynamic* Mat, const FVector& P, const FVector& S);
};

/** A traffic car turned into a physics body (box collision root, the vehicle mesh as a visual child). */
UCLASS()
class WEBHOMAGE_API ABruteCar : public AActor
{
	GENERATED_BODY()
public:
	ABruteCar();
	void InitFrom(const FWHTakenCar& Car);
	/** Held over the Brute's head: physics off, follows the given transform. */
	void SetHeld(bool bHeld);
	void Launch(const FVector& VelCm, const FVector& AngVelDeg = FVector::ZeroVector);
	UBoxComponent* Body() const { return Box; }
	float LenM = 4.8f, WidM = 1.85f;
	bool bBig = false;
	bool bThrown = false;
	float ThrownT = 0.f;
	virtual void Tick(float Dt) override;

private:
	UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> Box;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Mesh;
	float Age = 0.f, ImpactCd = 0.f;
	UFUNCTION() void OnHit(UPrimitiveComponent* Self, AActor* Other, UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit);
};

/** World helpers shared by the Brute's moves. */
namespace BruteWorld
{
	/** Pulls traffic cars within RadiusM of CenterCm out of the sim and returns them as physics cars (cap per call + global cap on live cars). */
	void TakeCars(UWorld* W, const FVector& CenterCm, float RadiusM, int32 MaxN, TArray<ABruteCar*>& Out);
	/** Radial blast: lifts nearby traffic cars into physics and pushes every physics car in range outward + up. Returns cars affected. */
	int32 Blast(UWorld* W, const FVector& CenterCm, float RadiusM, float SpeedMps, float UpMps, const FVector& ConeDir = FVector::ZeroVector, float ConeCos = -2.f, AActor* Ignore = nullptr);
	/** Collateral damage counter (dollars), shared for the HUD / telemetry. */
	double& Collateral();
}
