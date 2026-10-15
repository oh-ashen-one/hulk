// Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
#include "Brute/BruteFx.h"
#include "WebHomage.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

namespace BruteFx
{
	UMaterialInstanceDynamic* Mat(UObject* Outer, const FLinearColor& C, float Emissive)
	{
		static TWeakObjectPtr<UMaterialInterface> Base;
		if (!Base.IsValid())
		{
			UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Traversal/Materials/M_TravColor.M_TravColor"));
			if (!M) M = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
			Base = M;
		}
		UMaterialInstanceDynamic* D = UMaterialInstanceDynamic::Create(Base.Get(), Outer);
		if (D) { D->SetVectorParameterValue(TEXT("Color"), C); D->SetScalarParameterValue(TEXT("Emissive"), Emissive); }
		return D;
	}
	UStaticMesh* Cube() { static TWeakObjectPtr<UStaticMesh> M; if (!M.IsValid()) M = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")); return M.Get(); }
	UStaticMesh* Sphere() { static TWeakObjectPtr<UStaticMesh> M; if (!M.IsValid()) M = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere")); return M.Get(); }
	UStaticMesh* Cylinder() { static TWeakObjectPtr<UStaticMesh> M; if (!M.IsValid()) M = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder")); return M.Get(); }
}

namespace
{
	FRandomStream& Rng() { static FRandomStream R(20261015); return R; }
	TArray<TWeakObjectPtr<ABruteCar>>& LiveCars() { static TArray<TWeakObjectPtr<ABruteCar>> L; return L; }
	constexpr int32 MaxLiveCars = 48;
	constexpr float G = 1960.f; // cm/s^2 (Brute world gravity x2 reads heavier; debris only)
}

// ================================================================================================ shockwave
ABruteShockwave::ABruteShockwave()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

UStaticMeshComponent* ABruteShockwave::Add(UStaticMesh* M, UMaterialInstanceDynamic* Mat, const FVector& P, const FVector& S)
{
	UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
	C->SetupAttachment(RootComponent);
	C->SetUsingAbsoluteLocation(true); C->SetUsingAbsoluteRotation(true); C->SetUsingAbsoluteScale(true);
	C->SetStaticMesh(M);
	C->SetMaterial(0, Mat);
	C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	C->SetGenerateOverlapEvents(false);
	C->SetCastShadow(false);
	C->SetWorldLocation(P); C->SetWorldScale3D(S);
	C->RegisterComponent();
	Comps.Add(C);
	return C;
}

void ABruteShockwave::Init(float RadiusM, bool bCrater, const FVector& ConeDir, float Strength)
{
	Radius = FMath::Max(RadiusM, 2.f);
	FRandomStream& R = Rng();
	const FVector O = GetActorLocation();
	UMaterialInstanceDynamic* Dust = BruteFx::Mat(this, FLinearColor(0.32f, 0.29f, 0.25f));
	UMaterialInstanceDynamic* DustHi = BruteFx::Mat(this, FLinearColor(0.55f, 0.52f, 0.47f));
	UMaterialInstanceDynamic* Rock = BruteFx::Mat(this, FLinearColor(0.07f, 0.07f, 0.075f));
	UMaterialInstanceDynamic* Dark = BruteFx::Mat(this, FLinearColor(0.012f, 0.011f, 0.010f));
	const bool bCone = !ConeDir.IsNearlyZero();
	const FVector CF = bCone ? FVector(ConeDir.X, ConeDir.Y, 0).GetSafeNormal() : FVector::ForwardVector;
	const int32 NPuff = bCone ? 22 : FMath::Clamp(int32(Radius * 2.2f), 18, 48);
	for (int32 I = 0; I < NPuff; ++I)
	{
		float A = bCone ? FMath::DegreesToRadians(R.FRandRange(-32.f, 32.f)) + FMath::Atan2(CF.Y, CF.X) : (I + R.FRand() * 0.6f) / NPuff * 2.f * PI;
		const FVector Dir(FMath::Cos(A), FMath::Sin(A), 0.f);
		const float S = (bCone ? 1.4f : 0.9f + Radius * 0.05f) * R.FRandRange(0.8f, 1.3f);
		FPart Pt; Pt.Kind = 0; Pt.P = O + Dir * 80.f + FVector(0, 0, bCone ? 180.f : 40.f);
		Pt.V = Dir * (Radius * 100.f / (bCone ? 0.45f : 0.55f)) * R.FRandRange(0.75f, 1.1f) + FVector(0, 0, R.FRandRange(0.f, 120.f));
		Pt.S0 = FVector(S); Pt.Life = bCone ? 0.7f : 1.1f;
		Pt.C = Add(BruteFx::Sphere(), (I & 1) ? Dust : DustHi, Pt.P, Pt.S0 * 0.3f);
		Parts.Add(Pt);
	}
	if (!bCone)
	{
		const int32 NDeb = FMath::Clamp(int32(Radius * 1.4f * Strength), 10, 40);
		for (int32 I = 0; I < NDeb; ++I)
		{
			const float A = R.FRand() * 2.f * PI; const FVector Dir(FMath::Cos(A), FMath::Sin(A), 0.f);
			FPart Pt; Pt.Kind = 1; Pt.P = O + Dir * R.FRandRange(50.f, 250.f) + FVector(0, 0, 30.f);
			Pt.V = Dir * R.FRandRange(300.f, 1100.f) * Strength + FVector(0, 0, R.FRandRange(600.f, 1700.f) * Strength);
			const float S = R.FRandRange(0.15f, 0.6f);
			Pt.S0 = FVector(S, S * R.FRandRange(0.6f, 1.2f), S * R.FRandRange(0.4f, 0.9f)); Pt.Life = 4.f; Pt.Spin = R.FRandRange(-600.f, 600.f);
			Pt.C = Add(BruteFx::Cube(), Rock, Pt.P, Pt.S0);
			Parts.Add(Pt);
		}
	}
	if (bCrater)
	{
		bHasCrater = true;
		const float CR = FMath::Clamp(Radius * 0.32f, 2.f, 9.f);   // crater radius (m)
		FPart Pt; Pt.Kind = 2; Pt.P = O + FVector(0, 0, 3.f); Pt.S0 = FVector(CR * 2.f, CR * 2.f, 0.03f); Pt.Life = CraterLife;
		Pt.C = Add(BruteFx::Cylinder(), Dark, Pt.P, Pt.S0); Parts.Add(Pt);
		const int32 NCrack = 9 + int32(CR);
		for (int32 I = 0; I < NCrack; ++I)
		{
			const float A = (I + R.FRand() * 0.7f) / NCrack * 2.f * PI; const FVector Dir(FMath::Cos(A), FMath::Sin(A), 0.f);
			const float L = CR * R.FRandRange(1.2f, 2.6f);
			FPart K; K.Kind = 3; K.P = O + Dir * (CR * 100.f + L * 50.f) + FVector(0, 0, 2.5f); K.S0 = FVector(L, R.FRandRange(0.12f, 0.3f), 0.03f); K.Life = CraterLife;
			K.C = Add(BruteFx::Cube(), Dark, K.P, K.S0); K.C->SetWorldRotation(FRotator(0.f, FMath::RadiansToDegrees(A), 0.f)); Parts.Add(K);
		}
		const int32 NRim = 10 + int32(CR * 2.f);
		for (int32 I = 0; I < NRim; ++I)
		{
			const float A = (I + R.FRand() * 0.5f) / NRim * 2.f * PI; const FVector Dir(FMath::Cos(A), FMath::Sin(A), 0.f);
			const float S = R.FRandRange(0.4f, 1.1f) * FMath::Sqrt(CR / 3.f);
			FPart K; K.Kind = 4; K.P = O + Dir * CR * 100.f * R.FRandRange(0.9f, 1.1f) + FVector(0, 0, S * 15.f); K.S0 = FVector(S, S * 0.8f, S * 0.45f); K.Life = CraterLife;
			K.C = Add(BruteFx::Cube(), Rock, K.P, K.S0); K.C->SetWorldRotation(FRotator(R.FRandRange(-35.f, 35.f), FMath::RadiansToDegrees(A), R.FRandRange(-25.f, 25.f))); Parts.Add(K);
		}
	}
	SetLifeSpan(bCrater ? CraterLife + 2.f : 5.f);
}

void ABruteShockwave::Tick(float Dt)
{
	Super::Tick(Dt);
	Age += Dt;
	const float GZ = GetActorLocation().Z;
	for (FPart& P : Parts)
	{
		if (!P.C) continue;
		P.Age += Dt;
		const float K = FMath::Clamp(P.Age / P.Life, 0.f, 1.f);
		switch (P.Kind)
		{
		case 0: // dust puff: decelerates, grows, then shrinks away
			P.P += P.V * Dt; P.V *= FMath::Exp(-3.2f * Dt); P.V.Z -= 150.f * Dt;
			P.C->SetWorldLocation(P.P);
			P.C->SetWorldScale3D(P.S0 * (K < 0.35f ? FMath::Lerp(0.3f, 1.f, K / 0.35f) : FMath::Lerp(1.f, 0.f, (K - 0.35f) / 0.65f)) * (1.f + K));
			if (K >= 1.f) { P.C->SetVisibility(false); }
			break;
		case 1: // debris: ballistic, rests on the ground, shrinks at the end
			if (!P.bRest)
			{
				P.V.Z -= G * Dt; P.P += P.V * Dt;
				if (P.P.Z < GZ + P.S0.Z * 50.f && P.V.Z < 0.f) { P.P.Z = GZ + P.S0.Z * 50.f; if (FMath::Abs(P.V.Z) > 400.f) { P.V.Z *= -0.3f; P.V.X *= 0.5f; P.V.Y *= 0.5f; } else P.bRest = true; }
				P.C->SetWorldLocationAndRotation(P.P, FRotator(P.Age * P.Spin, P.Age * P.Spin * 0.7f, 0.f));
			}
			if (K > 0.8f) P.C->SetWorldScale3D(P.S0 * FMath::Max(0.f, 1.f - (K - 0.8f) / 0.2f));
			break;
		default: // crater / cracks / rim: pop in fast, persist, sink away at the end
		{
			const float In = FMath::Clamp(P.Age / 0.12f, 0.f, 1.f), Out = K > 0.92f ? FMath::Max(0.f, 1.f - (K - 0.92f) / 0.08f) : 1.f;
			FVector S = P.S0; if (P.Kind == 3) S.X *= In; else S *= In;
			P.C->SetWorldScale3D(S * Out);
		}
		}
	}
}

// ================================================================================================ physics car
ABruteCar::ABruteCar()
{
	PrimaryActorTick.bCanEverTick = true;
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Body"));
	RootComponent = Box;
	Box->SetCollisionProfileName(TEXT("PhysicsActor"));
	Box->SetNotifyRigidBodyCollision(true);
	Box->SetLinearDamping(0.05f); Box->SetAngularDamping(0.4f);
	Box->BodyInstance.bUseCCD = true;
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Box);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetGenerateOverlapEvents(false);
}

void ABruteCar::InitFrom(const FWHTakenCar& Car)
{
	LenM = Car.LenM; WidM = Car.WidM; bBig = Car.bBig;
	const float HalfH = bBig ? 150.f : 75.f;
	Box->SetBoxExtent(FVector(LenM * 50.f, WidM * 50.f, HalfH));
	Mesh->SetStaticMesh(Car.Mesh);
	if (Car.Material) for (int32 S = 0; S < Mesh->GetNumMaterials(); ++S) Mesh->SetMaterial(S, Car.Material);
	// the vehicle material reads per-instance custom data (paint r, g, b, brake); a plain component gets the same values as primitive data
	Mesh->SetCustomPrimitiveDataVector4(0, FVector4(Car.Color.R, Car.Color.G, Car.Color.B, 0.f));
	Mesh->SetRelativeLocation(FVector(0, 0, -HalfH));
	Box->SetMassOverrideInKg(NAME_None, bBig ? 9000.f : 1500.f, true);
	Box->SetSimulatePhysics(true);
	Box->OnComponentHit.AddDynamic(this, &ABruteCar::OnHit);
	SetLifeSpan(0.f);
}

void ABruteCar::SetHeld(bool bHeld)
{
	Box->SetSimulatePhysics(!bHeld);
	Box->SetCollisionEnabled(bHeld ? ECollisionEnabled::NoCollision : ECollisionEnabled::QueryAndPhysics);
	if (bHeld) { bThrown = false; Age = 0.f; }
}

void ABruteCar::Launch(const FVector& VelCm, const FVector& AngVelDeg)
{
	if (!Box->IsSimulatingPhysics()) { Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics); Box->SetSimulatePhysics(true); }
	Box->SetPhysicsLinearVelocity(VelCm);
	if (!AngVelDeg.IsNearlyZero()) Box->SetPhysicsAngularVelocityInDegrees(AngVelDeg);
	Age = 0.f;
}

void ABruteCar::Tick(float Dt)
{
	Super::Tick(Dt);
	Age += Dt; ImpactCd -= Dt;
	if (bThrown) ThrownT += Dt;
	if (Box->IsSimulatingPhysics())
	{
		if (Age > 75.f) Destroy();
		else if (GetActorLocation().Z < -20000.f) Destroy();
	}
}

void ABruteCar::OnHit(UPrimitiveComponent* Self, AActor* Other, UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit)
{
	if (ImpactCd > 0.f || !bThrown) return;
	const float Spd = Box->GetPhysicsLinearVelocity().Size() * 0.01f;
	if (ThrownT < 0.08f || Spd < 14.f) return;
	ImpactCd = 0.6f;
	UWorld* W = GetWorld(); if (!W) return;
	const FVector P = Hit.ImpactPoint;
	if (ABruteShockwave* S = W->SpawnActor<ABruteShockwave>(FVector(P.X, P.Y, P.Z - 60.f), FRotator::ZeroRotator)) S->Init(FMath::Clamp(Spd * 0.18f, 4.f, 10.f), false, FVector::ZeroVector, 0.6f);
	BruteWorld::Blast(W, P, FMath::Clamp(Spd * 0.2f, 4.f, 9.f), 10.f, 6.f, FVector::ZeroVector, -2.f, this);
	BruteWorld::Collateral() += 8000.0 + Spd * 400.0;
	UE_LOG(LogWebHomage, Display, TEXT("WH_BRUTE thrown car impact %.1f m/s at (%.0f %.0f %.0f)"), Spd, P.X, P.Y, P.Z);
	if (Spd < 25.f) bThrown = false;
}

// ================================================================================================ world helpers
namespace BruteWorld
{
	double& Collateral() { static double D = 0.0; return D; }

	void TakeCars(UWorld* W, const FVector& CenterCm, float RadiusM, int32 MaxN, TArray<ABruteCar*>& Out)
	{
		if (!W || MaxN <= 0) return;
		TArray<FWHTakenCar> Taken;
		for (TActorIterator<AWHLifeTraffic> It(W); It && Taken.Num() < MaxN; ++It) It->TakeCarsInRadius(CenterCm, RadiusM * 100.f, MaxN - Taken.Num(), Taken);
		TArray<TWeakObjectPtr<ABruteCar>>& L = LiveCars();
		L.RemoveAll([](const TWeakObjectPtr<ABruteCar>& C) { return !C.IsValid(); });
		for (const FWHTakenCar& T : Taken)
		{
			while (L.Num() >= MaxLiveCars) { if (ABruteCar* Old = L[0].Get()) Old->Destroy(); L.RemoveAt(0); }
			const float HalfH = T.bBig ? 150.f : 75.f;
			FActorSpawnParameters SP; SP.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			ABruteCar* C = W->SpawnActor<ABruteCar>(T.Xf.GetLocation() + FVector(0, 0, HalfH + 8.f), T.Xf.Rotator(), SP);
			if (!C) continue;
			C->InitFrom(T);
			C->Launch(T.VelCm);
			L.Add(C); Out.Add(C);
		}
	}

	int32 Blast(UWorld* W, const FVector& CenterCm, float RadiusM, float SpeedMps, float UpMps, const FVector& ConeDir, float ConeCos, AActor* Ignore)
	{
		if (!W) return 0;
		TArray<ABruteCar*> New;
		TakeCars(W, CenterCm, RadiusM, 14, New);
		const FVector CF = FVector(ConeDir.X, ConeDir.Y, 0).GetSafeNormal();
		int32 N = 0;
		for (TActorIterator<ABruteCar> It(W); It; ++It)
		{
			ABruteCar* C = *It; if (C == Ignore || !C->Body() || !C->Body()->IsSimulatingPhysics()) continue;
			FVector D = C->GetActorLocation() - CenterCm; const float Dist = D.Size() * 0.01f;
			if (Dist > RadiusM) continue;
			FVector H(D.X, D.Y, 0); H = H.SizeSquared() > 1.f ? H.GetSafeNormal() : (CF.IsNearlyZero() ? FVector::ForwardVector : CF);
			if (!CF.IsNearlyZero() && FVector::DotProduct(H, CF) < ConeCos) continue;
			const float K = FMath::Max(0.3f, 1.f - Dist / RadiusM) * (C->bBig ? 0.45f : 1.f);
			const FVector Dv = (H * SpeedMps + FVector(0, 0, UpMps)) * K * 100.f;
			C->Body()->AddImpulse(Dv, NAME_None, true);
			C->Body()->AddAngularImpulseInDegrees(FVector(FMath::FRandRange(-300.f, 300.f), FMath::FRandRange(-300.f, 300.f), FMath::FRandRange(-200.f, 200.f)) * K, NAME_None, true);
			C->bThrown = true; C->ThrownT = 0.f;
			Collateral() += 6000.0 * K;
			++N;
		}
		return N;
	}
}
