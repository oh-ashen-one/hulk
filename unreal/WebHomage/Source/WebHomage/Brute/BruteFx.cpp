// Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
#include "Brute/BruteFx.h"
#include "WebHomage.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Characters/WHCharAnimInstance.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
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
	UStaticMesh* FxMesh(const TCHAR* Name)
	{
		static TMap<FString, TWeakObjectPtr<UStaticMesh>> Cache;
		TWeakObjectPtr<UStaticMesh>& W = Cache.FindOrAdd(Name);
		if (!W.IsValid()) W = LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("/Game/Brute/Fx/%s.%s"), Name, Name));
		return W.Get();
	}
	UMaterialInstanceDynamic* FxMat(UObject* Outer, bool bDust, const FLinearColor& C, float Opacity, float Glow)
	{
		static TWeakObjectPtr<UMaterialInterface> Shock, Dust;
		TWeakObjectPtr<UMaterialInterface>& B = bDust ? Dust : Shock;
		if (!B.IsValid()) B = LoadObject<UMaterialInterface>(nullptr, bDust ? TEXT("/Game/Brute/Fx/M_BruteDust.M_BruteDust") : TEXT("/Game/Brute/Fx/M_BruteShock.M_BruteShock"));
		if (!B.IsValid()) return nullptr;
		UMaterialInstanceDynamic* D = UMaterialInstanceDynamic::Create(B.Get(), Outer);
		D->SetVectorParameterValue(TEXT("Color"), C); D->SetScalarParameterValue(TEXT("Opacity"), Opacity); D->SetScalarParameterValue(TEXT("Glow"), Glow);
		return D;
	}
}

namespace
{
	FRandomStream& Rng() { static FRandomStream R(20261015); return R; }
	inline float EaseOutF(float X) { X = FMath::Clamp(X, 0.f, 1.f); return 1.f - (1.f - X) * (1.f - X) * (1.f - X); }
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
	UMaterialInstanceDynamic* Rock = BruteFx::Mat(this, FLinearColor(0.06f, 0.058f, 0.055f));
	UMaterialInstanceDynamic* Dark = BruteFx::Mat(this, FLinearColor(0.012f, 0.011f, 0.010f));
	UStaticMesh* PuffM = BruteFx::FxMesh(TEXT("SM_BruteFx_Puff"));
	UStaticMesh* RockM = BruteFx::FxMesh(TEXT("SM_BruteFx_Rock"));
	UStaticMesh* RingM = BruteFx::FxMesh(TEXT("SM_BruteFx_Ring"));
	UStaticMesh* ArcM = BruteFx::FxMesh(TEXT("SM_BruteFx_Arc"));
	UStaticMesh* CraterM = BruteFx::FxMesh(TEXT("SM_BruteFx_Crater"));
	const bool bCone = !ConeDir.IsNearlyZero();
	const FVector CF = bCone ? FVector(ConeDir.X, ConeDir.Y, 0).GetSafeNormal() : FVector::ForwardVector;
	const float CYaw = FMath::RadiansToDegrees(FMath::Atan2(CF.Y, CF.X));
	const FLinearColor DustC(0.36f, 0.33f, 0.28f), ShockC(1.0f, 0.95f, 0.85f);

	// shockwave walls: a fast bright band + a slower dusty one (full ring), or stacked forward arcs (clap cone)
	if (RingM && ArcM)
	{
		const int32 NW = bCone ? 3 : 2;
		for (int32 I = 0; I < NW; ++I)
		{
			FPart W; W.Kind = bCone ? 7 : (I == 0 ? 5 : 6); W.P = O + FVector(0, 0, bCone ? 40.f : 5.f) + (bCone ? FVector(CF * 100.f) : FVector::ZeroVector);
			W.Delay = I * (bCone ? 0.07f : 0.05f); W.Life = (bCone ? 0.55f : (I == 0 ? 0.45f : 0.9f)) * FMath::Sqrt(FMath::Max(Strength, 0.4f));
			W.R1 = Radius * (bCone ? 1.f : (I == 0 ? 1.f : 0.7f));
			const float Hgt = bCone ? 4.0f : (I == 0 ? 1.1f + Radius * 0.04f : 2.2f + Radius * 0.08f);
			W.S0 = FVector(1.f, 1.f, Hgt);
			W.Op0 = W.Kind == 6 ? 0.38f : (bCone ? 0.7f : 0.55f);
			W.M = BruteFx::FxMat(this, W.Kind == 6, W.Kind == 6 ? DustC : ShockC, W.Op0, W.Kind == 6 ? 3.2f : (bCone ? 20.f : 9.f));
			W.C = Add(bCone ? ArcM : RingM, nullptr, W.P, FVector(0.01f));
			if (W.M) W.C->SetMaterial(0, W.M);
			if (bCone) W.C->SetWorldRotation(FRotator(0.f, CYaw, 0.f));
			W.C->SetVisibility(false);
			Parts.Add(W);
		}
	}
	// dust puffs (soft translucent balls rolling outward, growing and fading)
	const int32 NPuff = bCone ? 18 : FMath::Clamp(int32(Radius * 1.8f), 14, 40);
	for (int32 I = 0; I < NPuff; ++I)
	{
		const float A = bCone ? FMath::DegreesToRadians(R.FRandRange(-34.f, 34.f) + CYaw) : (I + R.FRand() * 0.6f) / NPuff * 2.f * PI;
		const FVector Dir(FMath::Cos(A), FMath::Sin(A), 0.f);
		const float S = (bCone ? 1.1f : 0.7f + Radius * 0.04f) * R.FRandRange(0.7f, 1.3f);
		FPart Pt; Pt.Kind = 0; Pt.P = O + Dir * 120.f + FVector(0, 0, bCone ? 150.f : 60.f);
		Pt.V = Dir * (Radius * 100.f / (bCone ? 0.5f : 0.8f)) * R.FRandRange(0.6f, 1.05f) + FVector(0, 0, R.FRandRange(20.f, 180.f));
		Pt.S0 = FVector(S, S, S * 0.7f); Pt.Life = (bCone ? 0.7f : 1.4f) * R.FRandRange(0.85f, 1.2f); Pt.Op0 = R.FRandRange(0.25f, 0.45f);
		Pt.M = PuffM ? BruteFx::FxMat(this, true, DustC * R.FRandRange(0.8f, 1.15f), Pt.Op0, 3.2f) : nullptr;
		Pt.C = Add(PuffM ? PuffM : BruteFx::Sphere(), Pt.M ? Pt.M.Get() : BruteFx::Mat(this, DustC * 0.4f), Pt.P, Pt.S0 * 0.3f);
		Parts.Add(Pt);
	}
	if (!bCone)
	{	// lingering dust over the impact
		const int32 NL = bCrater ? 7 : 3;
		for (int32 I = 0; I < NL; ++I)
		{
			const float A = R.FRand() * 2.f * PI; const float D = R.FRandRange(0.f, Radius * 30.f);
			FPart Pt; Pt.Kind = 0; Pt.P = O + FVector(FMath::Cos(A) * D, FMath::Sin(A) * D, 80.f); Pt.V = FVector(FMath::Cos(A), FMath::Sin(A), 0.6f) * R.FRandRange(60.f, 160.f);
			const float S = 1.4f + Radius * 0.07f; Pt.S0 = FVector(S, S, S * 0.75f); Pt.Life = R.FRandRange(2.2f, 3.2f); Pt.Op0 = 0.25f; Pt.Delay = R.FRandRange(0.f, 0.25f);
			Pt.M = PuffM ? BruteFx::FxMat(this, true, DustC * 0.9f, Pt.Op0, 3.0f) : nullptr;
			Pt.C = Add(PuffM ? PuffM : BruteFx::Sphere(), Pt.M ? Pt.M.Get() : BruteFx::Mat(this, DustC * 0.4f), Pt.P, FVector(0.01f));
			Parts.Add(Pt);
		}
		const int32 NDeb = FMath::Clamp(int32(Radius * 1.4f * Strength), 10, 40);
		for (int32 I = 0; I < NDeb; ++I)
		{
			const float A = R.FRand() * 2.f * PI; const FVector Dir(FMath::Cos(A), FMath::Sin(A), 0.f);
			FPart Pt; Pt.Kind = 1; Pt.P = O + Dir * R.FRandRange(50.f, 250.f) + FVector(0, 0, 30.f);
			Pt.V = Dir * R.FRandRange(300.f, 1100.f) * Strength + FVector(0, 0, R.FRandRange(600.f, 1700.f) * Strength);
			const float S = R.FRandRange(0.25f, 0.8f) * (RockM ? 1.f : 0.6f);
			Pt.S0 = FVector(S, S * R.FRandRange(0.7f, 1.2f), S * R.FRandRange(0.6f, 1.f)); Pt.Life = 4.f; Pt.Spin = R.FRandRange(-600.f, 600.f);
			Pt.C = Add(RockM ? RockM : BruteFx::Cube(), Rock, Pt.P, Pt.S0);
			Parts.Add(Pt);
		}
	}
	if (bCrater)
	{
		bHasCrater = true;
		const float CR = FMath::Clamp(Radius * 0.17f, 1.6f, 4.5f);   // crater radius (m)
		FPart Pt; Pt.Kind = 2; Pt.P = O + FVector(0, 0, 4.f); Pt.Life = CraterLife;
		if (CraterM) { Pt.S0 = FVector(CR, CR, FMath::Min(CR * 0.08f, 0.3f)); Pt.C = Add(CraterM, Dark, Pt.P, Pt.S0); Pt.C->SetWorldRotation(FRotator(0.f, R.FRandRange(0.f, 360.f), 0.f)); }
		else { Pt.S0 = FVector(CR * 2.f, CR * 2.f, 0.03f); Pt.C = Add(BruteFx::Cylinder(), Dark, Pt.P, Pt.S0); }
		Parts.Add(Pt);
		const int32 NCrack = 8 + int32(CR * 1.5f);
		for (int32 I = 0; I < NCrack; ++I)
		{
			const float A = (I + R.FRand() * 0.7f) / NCrack * 2.f * PI; const FVector Dir(FMath::Cos(A), FMath::Sin(A), 0.f);
			const float L = CR * R.FRandRange(1.0f, 2.4f);
			FPart K; K.Kind = 3; K.P = O + Dir * (CR * 100.f + L * 50.f) + FVector(0, 0, 3.f); K.S0 = FVector(L, R.FRandRange(0.08f, 0.2f), 0.025f); K.Life = CraterLife;
			K.C = Add(BruteFx::Cube(), Dark, K.P, K.S0); K.C->SetWorldRotation(FRotator(0.f, FMath::RadiansToDegrees(A) + R.FRandRange(-8.f, 8.f), 0.f)); Parts.Add(K);
		}
		const int32 NRim = 8 + int32(CR * 2.f);
		for (int32 I = 0; I < NRim; ++I)
		{
			const float A = (I + R.FRand() * 0.5f) / NRim * 2.f * PI; const FVector Dir(FMath::Cos(A), FMath::Sin(A), 0.f);
			const float S = R.FRandRange(0.25f, 0.6f) * FMath::Sqrt(CR / 3.f);
			FPart K; K.Kind = 4; K.P = O + Dir * CR * 100.f * R.FRandRange(0.95f, 1.2f) + FVector(0, 0, S * 12.f); K.S0 = FVector(S, S * 0.8f, S * 0.5f); K.Life = CraterLife;
			K.C = Add(RockM ? RockM : BruteFx::Cube(), Rock, K.P, K.S0); K.C->SetWorldRotation(FRotator(R.FRandRange(-35.f, 35.f), FMath::RadiansToDegrees(A), R.FRandRange(-25.f, 25.f))); Parts.Add(K);
		}
	}
	SetLifeSpan(bCrater ? CraterLife + 2.f : 5.f);
}

void ABruteShockwave::InitWall(const FVector& Normal, float SizeM)
{
	FRandomStream& R = Rng();
	const FVector O = GetActorLocation(), N = Normal.GetSafeNormal();
	const FVector U = FVector::CrossProduct(N, FVector::UpVector).GetSafeNormal(), V = FVector::CrossProduct(U, N);   // wall plane: U along, V up
	UMaterialInstanceDynamic* Rock = BruteFx::Mat(this, FLinearColor(0.07f, 0.065f, 0.06f));
	UMaterialInstanceDynamic* Dark = BruteFx::Mat(this, FLinearColor(0.012f, 0.011f, 0.010f));
	UStaticMesh* PuffM = BruteFx::FxMesh(TEXT("SM_BruteFx_Puff"));
	UStaticMesh* RockM = BruteFx::FxMesh(TEXT("SM_BruteFx_Rock"));
	UStaticMesh* CraterM = BruteFx::FxMesh(TEXT("SM_BruteFx_Crater"));
	const FLinearColor DustC(0.30f, 0.28f, 0.25f);
	bHasCrater = true; CraterLife = 25.f;
	const float CR = FMath::Clamp(SizeM, 0.5f, 2.5f);
	{	// crater: the ground crater mesh turned onto the wall (its up axis = the wall normal), sunk a little into the face
		FPart Pt; Pt.Kind = 2; Pt.P = O + N * 3.f; Pt.Life = CraterLife;
		if (CraterM) { Pt.S0 = FVector(CR, CR, FMath::Min(CR * 0.12f, 0.25f)); Pt.C = Add(CraterM, Dark, Pt.P, Pt.S0); }
		else { Pt.S0 = FVector(CR * 2.f, CR * 2.f, 0.04f); Pt.C = Add(BruteFx::Cylinder(), Dark, Pt.P, Pt.S0); }
		Pt.C->SetWorldRotation(FRotationMatrix::MakeFromZX(N, U.RotateAngleAxis(R.FRandRange(0.f, 360.f), N)).Rotator());
		Parts.Add(Pt);
	}
	const int32 NCrack = 7 + int32(CR * 3.f);
	for (int32 I = 0; I < NCrack; ++I)
	{
		const float A = (I + R.FRand() * 0.7f) / NCrack * 2.f * PI; const FVector Dir = U * FMath::Cos(A) + V * FMath::Sin(A);
		const float L = CR * R.FRandRange(0.9f, 2.6f);
		FPart K; K.Kind = 3; K.P = O + Dir * (CR * 80.f + L * 50.f) + N * 2.f; K.S0 = FVector(L, R.FRandRange(0.05f, 0.14f), 0.025f); K.Life = CraterLife;
		K.C = Add(BruteFx::Cube(), Dark, K.P, K.S0); K.C->SetWorldRotation(FRotationMatrix::MakeFromXZ(Dir, N).Rotator()); Parts.Add(K);
	}
	for (int32 I = 0; I < 10; ++I)
	{	// rubble knocked out of the wall: flies out, then falls (no floor at punch height: it just drops away and shrinks)
		FPart Pt; Pt.Kind = 8; Pt.P = O + N * 30.f + (U * R.FRandRange(-1.f, 1.f) + V * R.FRandRange(-1.f, 1.f)) * CR * 60.f;
		Pt.V = N * R.FRandRange(250.f, 700.f) + U * R.FRandRange(-250.f, 250.f) + FVector(0, 0, R.FRandRange(-100.f, 400.f));
		const float S = R.FRandRange(0.15f, 0.45f) * (RockM ? 1.f : 0.6f) * FMath::Sqrt(CR);
		Pt.S0 = FVector(S, S * R.FRandRange(0.7f, 1.2f), S * R.FRandRange(0.6f, 1.f)); Pt.Life = 2.4f; Pt.Spin = R.FRandRange(-700.f, 700.f);
		Pt.C = Add(RockM ? RockM : BruteFx::Cube(), Rock, Pt.P, Pt.S0); Parts.Add(Pt);
	}
	for (int32 I = 0; I < 6; ++I)
	{	// dust burst out of the hole
		FPart Pt; Pt.Kind = 0; Pt.P = O + N * 40.f;
		Pt.V = (N * R.FRandRange(1.f, 2.f) + U * R.FRandRange(-1.f, 1.f) + V * R.FRandRange(-0.6f, 1.f)).GetSafeNormal() * R.FRandRange(250.f, 650.f);
		const float S = R.FRandRange(0.7f, 1.3f) * (0.6f + CR * 0.4f); Pt.S0 = FVector(S, S, S * 0.8f); Pt.Life = R.FRandRange(0.8f, 1.4f); Pt.Op0 = R.FRandRange(0.16f, 0.28f);
		Pt.M = PuffM ? BruteFx::FxMat(this, true, DustC * R.FRandRange(0.85f, 1.1f), Pt.Op0, 3.2f) : nullptr;
		Pt.C = Add(PuffM ? PuffM : BruteFx::Sphere(), Pt.M ? Pt.M.Get() : BruteFx::Mat(this, DustC * 0.4f), Pt.P, Pt.S0 * 0.3f);
		Parts.Add(Pt);
	}
	SetLifeSpan(CraterLife + 2.f);
}

void ABruteShockwave::Tick(float Dt)
{
	Super::Tick(Dt);
	Age += Dt;
	const float GZ = GetActorLocation().Z;
	for (FPart& P : Parts)
	{
		if (!P.C) continue;
		if (P.Delay > 0.f) { P.Delay -= Dt; continue; }
		P.Age += Dt;
		const float K = FMath::Clamp(P.Age / P.Life, 0.f, 1.f);
		switch (P.Kind)
		{
		case 0: // dust puff: decelerates, grows, fades (translucent) / shrinks (opaque fallback)
		{
			P.P += P.V * Dt; P.V *= FMath::Exp(-2.6f * Dt); P.V.Z -= 40.f * Dt;
			P.C->SetWorldLocation(P.P);
			const float Grow = FMath::Lerp(0.35f, 1.6f, EaseOutF(K));
			if (P.M) { P.C->SetWorldScale3D(P.S0 * Grow); P.M->SetScalarParameterValue(TEXT("Opacity"), P.Op0 * (K < 0.15f ? K / 0.15f : FMath::Square(1.f - (K - 0.15f) / 0.85f))); }
			else P.C->SetWorldScale3D(P.S0 * Grow * FMath::Square(1.f - K));
			if (K >= 1.f) P.C->SetVisibility(false);
			break;
		}
		case 1: // debris: ballistic, rests on the ground, shrinks at the end
			if (!P.bRest)
			{
				P.V.Z -= G * Dt; P.P += P.V * Dt;
				if (P.P.Z < GZ + P.S0.Z * 40.f && P.V.Z < 0.f) { P.P.Z = GZ + P.S0.Z * 40.f; if (FMath::Abs(P.V.Z) > 400.f) { P.V.Z *= -0.3f; P.V.X *= 0.5f; P.V.Y *= 0.5f; } else P.bRest = true; }
				P.C->SetWorldLocationAndRotation(P.P, FRotator(P.Age * P.Spin, P.Age * P.Spin * 0.7f, 0.f));
			}
			if (K > 0.8f) P.C->SetWorldScale3D(P.S0 * FMath::Max(0.f, 1.f - (K - 0.8f) / 0.2f));
			break;
		case 8: // wall rubble: ballistic, never rests, shrinks away
			P.V.Z -= G * Dt; P.P += P.V * Dt;
			P.C->SetWorldLocationAndRotation(P.P, FRotator(P.Age * P.Spin, P.Age * P.Spin * 0.7f, 0.f));
			P.C->SetWorldScale3D(P.S0 * (K > 0.6f ? FMath::Max(0.f, 1.f - (K - 0.6f) / 0.4f) : 1.f));
			break;
		case 5: case 6: case 7: // expanding shock walls
		{
			P.C->SetVisibility(K < 1.f);
			const float E = EaseOutF(K);
			const float Rr = FMath::Lerp(1.2f, P.R1, E);
			P.C->SetWorldScale3D(FVector(Rr, Rr, P.S0.Z * FMath::Lerp(1.f, P.Kind == 6 ? 1.6f : 0.35f, K)));
			if (P.M) P.M->SetScalarParameterValue(TEXT("Opacity"), P.Op0 * FMath::Square(1.f - K));
			break;
		}
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
	Mesh = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Mesh"));
	Mesh->NumCustomDataFloats = 4;
	Mesh->SetMobility(EComponentMobility::Movable);
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
	Mesh->SetRelativeLocation(FVector(0, 0, -HalfH));
	Mesh->ClearInstances();
	Mesh->AddInstance(FTransform::Identity, false);
	const float Cd[4] = { Car.Color.R, Car.Color.G, Car.Color.B, 0.f };
	Mesh->SetCustomData(0, TConstArrayView<float>(Cd, 4), true);
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

// ================================================================================================ flung pedestrian
ABruteFlung::ABruteFlung()
{
	PrimaryActorTick.bCanEverTick = true;
	Body = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Body"));
	RootComponent = Body;
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void ABruteFlung::Init(const FWHFlungWalker& W, const FVector& VelCm)
{
	Body->SetSkeletalMesh(W.Mesh);
	if (W.Anim) { Body->SetAnimationMode(EAnimationMode::AnimationBlueprint); Body->SetAnimInstanceClass(W.Anim); }
	if (W.Material) for (int32 I = 0; I < FMath::Max(1, Body->GetNumMaterials()); ++I) Body->SetMaterial(I, W.Material);
	Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	if (UWHCharAnimInstance* AI = Cast<UWHCharAnimInstance>(Body->GetAnimInstance())) AI->ForcedSpeed = 0.f;
	Scale = W.Scale; GroundZ = W.PosCm.Z; Vel = VelCm; Rot = FRotator(0.f, W.YawDeg, 0.f);
	FRandomStream& R = Rng();
	Spin = FVector(R.FRandRange(-540.f, 540.f), R.FRandRange(-200.f, 200.f), R.FRandRange(-720.f, 720.f));
	SetActorLocationAndRotation(W.PosCm, Rot); SetActorScale3D(FVector(Scale));
	SetLifeSpan(12.f);
}

void ABruteFlung::Tick(float Dt)
{
	Super::Tick(Dt);
	Age += Dt;
	FVector P = GetActorLocation();
	if (RestT < 0.f)
	{
		Vel.Z -= 980.f * 1.6f * Dt; P += Vel * Dt;
		Rot.Pitch += Spin.X * Dt; Rot.Yaw += Spin.Z * Dt; Rot.Roll += Spin.Y * Dt;
		if (P.Z <= GroundZ && Vel.Z < 0.f)
		{
			P.Z = GroundZ;
			if (Vel.Z < -500.f) { Vel.Z *= -0.25f; Vel.X *= 0.5f; Vel.Y *= 0.5f; Spin *= 0.4f; }
			else { RestT = 0.f; Rot = FRotator(-90.f, Rot.Yaw, 0.f); P.Z = GroundZ + 18.f; }   // flat on the back
		}
		SetActorLocationAndRotation(P, Rot);
	}
	else
	{
		RestT += Dt;
		if (RestT > 3.5f) SetActorScale3D(FVector(Scale * FMath::Max(0.01f, 1.f - (RestT - 3.5f) / 0.6f)));
		if (RestT > 4.1f) Destroy();
	}
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

	int32 Blast(UWorld* W, const FVector& CenterCm, float RadiusM, float SpeedMps, float UpMps, const FVector& ConeDir, float ConeCos, AActor* Ignore, bool bScare)
	{
		if (!W) return 0;
		TArray<ABruteCar*> New;
		TakeCars(W, CenterCm, RadiusM, 14, New);
		if (bScare)
		{	// the crowd: knocked over near the blast, running away further out
			TArray<FWHFlungWalker> Knocked;
			const bool bConeB = !ConeDir.IsNearlyZero();
			for (TActorIterator<AWHLifeCrowd> It(W); It; ++It) It->Panic(CenterCm, RadiusM * (bConeB ? 0.5f : 0.7f), RadiusM * 2.5f + 15.f, Knocked);
			const FVector CF0 = FVector(ConeDir.X, ConeDir.Y, 0).GetSafeNormal();
			for (const FWHFlungWalker& K : Knocked)
			{
				FVector H = K.PosCm - CenterCm; H.Z = 0; const float Dm = H.Size() * 0.01f; H = H.SizeSquared() > 1.f ? H.GetSafeNormal() : FVector::ForwardVector;
				if (bConeB && FVector::DotProduct(H, CF0) < ConeCos) continue;
				const float Kf = FMath::Max(0.35f, 1.f - Dm / RadiusM);
				FActorSpawnParameters SP; SP.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
				if (ABruteFlung* F = W->SpawnActor<ABruteFlung>(K.PosCm, FRotator::ZeroRotator, SP))
					F->Init(K, (H * FMath::Min(SpeedMps, 22.f) * 0.8f + FVector(0, 0, FMath::Max(UpMps, 6.f))) * Kf * 100.f);
				Collateral() += 500.0;
			}
		}
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
