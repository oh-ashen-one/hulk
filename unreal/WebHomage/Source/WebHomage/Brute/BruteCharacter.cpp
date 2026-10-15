// Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
#include "Brute/BruteCharacter.h"
#include "Brute/BruteFx.h"
#include "WebHomage.h"

#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "HAL/IConsoleManager.h"
#include "InputCoreTypes.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	inline float Smooth01(float X) { X = FMath::Clamp(X, 0.f, 1.f); return X * X * (3.f - 2.f * X); }
	inline float EaseOut(float X) { X = FMath::Clamp(X, 0.f, 1.f); return 1.f - (1.f - X) * (1.f - X); }
	inline FVector H2(const FVector& V) { return FVector(V.X, V.Y, 0.0); }
	inline double Approach(double V, double T, double Rate, double Dt) { return V + (T - V) * (1.0 - FMath::Exp(-Rate * Dt)); }
	const double CarHalfH = 0.75;
}

void FBrutePose::Blend(const FBrutePose& T, float A)
{
	auto L = [A](float& V, float To) { V += (To - V) * A; };
	L(RootZ, T.RootZ); L(RootPitch, T.RootPitch); L(RootRoll, T.RootRoll);
	L(SpinePitch, T.SpinePitch); L(SpineYaw, T.SpineYaw); L(SpineRoll, T.SpineRoll); L(HeadPitch, T.HeadPitch);
	for (int32 S = 0; S < 2; ++S)
	{
		L(ShPitch[S], T.ShPitch[S]); L(ShAbd[S], T.ShAbd[S]); L(ShYaw[S], T.ShYaw[S]); L(Elbow[S], T.Elbow[S]);
		L(HipPitch[S], T.HipPitch[S]); L(HipAbd[S], T.HipAbd[S]); L(Knee[S], T.Knee[S]);
	}
}

ABruteCharacter::ABruteCharacter()
{
	GetCapsuleComponent()->InitCapsuleSize(75.f, 128.f);
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GetCharacterMovement()->GravityScale = 0.f;
	CameraBoom->TargetArmLength = 750.f;
	CameraBoom->bDoCollisionTest = false;
	CameraBoom->bEnableCameraLag = true;
	CameraBoom->CameraLagSpeed = 12.f;
	CameraBoom->CameraLagMaxDistance = 220.f;
	CameraBoom->TargetOffset = FVector(0.f, 0.f, 95.f);
	CameraBoom->SocketOffset = FVector(0.f, 55.f, 30.f);
	FollowCamera->SetFieldOfView(72.f);
}

// ================================================================================================ lifecycle
void ABruteCharacter::BeginPlay()
{
	Super::BeginPlay();
	if (ProxyBody) ProxyBody->SetVisibility(false);
	GetCharacterMovement()->SetMovementMode(MOVE_None);
	GetCharacterMovement()->SetComponentTickEnabled(false);
	BuildRig();

	World.Init(GetWorld(), this);
	bWorldReady = World.Ok();
	for (ULevel* L : GetWorld()->GetLevels()) IndexCrowns(L);
	LevelAddedHandle = FWorldDelegates::LevelAddedToWorld.AddUObject(this, &ABruteCharacter::OnLevelAdded);
	LevelRemovedHandle = FWorldDelegates::LevelRemovedFromWorld.AddUObject(this, &ABruteCharacter::OnLevelRemoved);

	{ FString Tune; if (FParse::Value(FCommandLine::Get(), TEXT("-WHBruteTune="), Tune))
	{
		TArray<FString> Kv; Tune.ParseIntoArray(Kv, TEXT(","), true);
		for (const FString& S : Kv) { FString K, V; if (!S.Split(TEXT("="), &K, &V)) continue; const float F = FCString::Atof(*V);
			if (K == TEXT("Gravity")) Gravity = F; else if (K == TEXT("SprintSpeed")) SprintSpeed = F; else if (K == TEXT("SuperJumpHeight")) SuperJumpHeight = F;
			else if (K == TEXT("SuperJumpRange")) SuperJumpRange = F; else if (K == TEXT("ThrowSpeed")) ThrowSpeed = F; else if (K == TEXT("RunSpeed")) RunSpeed = F; }
	} }

	FString ScriptPath;
	if (FParse::Value(FCommandLine::Get(), TEXT("-WHBruteScript="), ScriptPath)) LoadScript(ScriptPath);
	FParse::Value(FCommandLine::Get(), TEXT("-WHBruteCsv="), CsvPath);
	if (CsvPath.IsEmpty() && bScript)
	{
		FString Dir, Name; if (FParse::Value(FCommandLine::Get(), TEXT("WHShotDir="), Dir)) { FParse::Value(FCommandLine::Get(), TEXT("WHShotName="), Name); CsvPath = Dir / (Name.IsEmpty() ? TEXT("brute") : Name) + TEXT("_brute.csv"); }
	}

	// spawn: the player start (feet), a script spawn, or the Times Square plaza
	Pos = (GetActorLocation() - FVector(0, 0, GetCapsuleComponent()->GetScaledCapsuleHalfHeight())) / 100.0;
	Facing = FMath::DegreesToRadians(GetActorRotation().Yaw);
	if (FParse::Param(FCommandLine::Get(), TEXT("WHSpawnTimesSquare"))) { Pos = FVector(-20.0, -230.0, 1.5); Facing = HALF_PI; }
	if (bHasSpawn) { Pos = SpawnPos; Facing = FMath::DegreesToRadians(SpawnYaw); }
	LastSafe = Pos;
	if (bWorldReady) { const double G = Floor(Pos, 3.0); if (G > -900.0 && G > Pos.Z - 4.0) Pos.Z = G; }
	SetMode(EBruteMode::Ground);
	CamYaw = FMath::RadiansToDegrees(Facing);
	if (APlayerController* PC = Cast<APlayerController>(Controller)) PC->SetControlRotation(FRotator(CamPitch, CamYaw, 0.0));
	UE_LOG(LogWebHomage, Display, TEXT("WH_BRUTE BeginPlay pos (%.1f %.1f %.1f) m facing %.0f deg, world boxes %d, script %d (%d keys), csv '%s'"),
		Pos.X, Pos.Y, Pos.Z, FMath::RadiansToDegrees(Facing), World.Boxes.Num(), bScript ? 1 : 0, Script.Num(), *CsvPath);
}

void ABruteCharacter::EndPlay(const EEndPlayReason::Type Reason)
{
	if (LevelAddedHandle.IsValid()) FWorldDelegates::LevelAddedToWorld.Remove(LevelAddedHandle);
	if (LevelRemovedHandle.IsValid()) FWorldDelegates::LevelRemovedFromWorld.Remove(LevelRemovedHandle);
	if (!CsvPath.IsEmpty() && CsvRows.Num())
	{
		FFileHelper::SaveStringToFile(TEXT("t,x,y,z,vx,vy,vz,speed,mode,act,charge,chain,dashes,held,apex,collateral,event\n") + FString::Join(CsvRows, TEXT("\n")) + TEXT("\n"), *CsvPath);
		UE_LOG(LogWebHomage, Display, TEXT("WH_BRUTE telemetry %d rows -> %s"), CsvRows.Num(), *CsvPath);
	}
	Super::EndPlay(Reason);
}

void ABruteCharacter::OnLevelAdded(ULevel* L, UWorld* W)
{
	if (W == GetWorld() && L && !L->IsPersistentLevel()) { World.AddLevel(L); bWorldReady = World.Ok(); IndexCrowns(L); }
}

void ABruteCharacter::OnLevelRemoved(ULevel* L, UWorld* W)
{
	FBox B(ForceInit);
	if (W == GetWorld() && L) World.RemoveLevel(L, B);
}

void ABruteCharacter::IndexCrowns(ULevel* L)
{
	if (!L) return;
	const int32 N0 = NCrowns;
	for (AActor* A : L->Actors)
	{
		if (!A) continue;
		TInlineComponentArray<UInstancedStaticMeshComponent*> Is(A);
		for (UInstancedStaticMeshComponent* IC : Is)
		{
			const UStaticMesh* SM = IC ? IC->GetStaticMesh() : nullptr;
			if (!SM) continue;
			const FString Nm = SM->GetName().ToLower();
			if (!(Nm.Contains(TEXT("leaves")) || Nm.Contains(TEXT("crown")) || Nm.Contains(TEXT("canopy")) || Nm.Contains(TEXT("foliage")))) continue;
			const FBoxSphereBounds MB = SM->GetBounds();
			for (int32 K = 0; K < IC->GetInstanceCount(); ++K)
			{
				FTransform T; if (!IC->GetInstanceTransform(K, T, true)) continue;
				const FVector C = T.TransformPosition(MB.Origin) / 100.0;
				const double Rr = 0.75 * MB.SphereRadius * T.GetScale3D().GetMax() / 100.0;
				if (Rr < 0.5 || Rr > 25.0) continue;
				const int64 Key = (int64(FMath::FloorToInt(C.X / 16.0)) << 32) ^ int64(uint32(FMath::FloorToInt(C.Y / 16.0)));
				Crowns.FindOrAdd(Key).Add(FVector4(C.X, C.Y, C.Z, Rr)); ++NCrowns;
			}
		}
	}
	if (NCrowns > N0) UE_LOG(LogWebHomage, Display, TEXT("WH_BRUTE tree crowns indexed: +%d (total %d)"), NCrowns - N0, NCrowns);
}

bool ABruteCharacter::SegHitsCrown(const FVector& A, const FVector& B) const
{
	if (NCrowns == 0) return false;
	const int32 X0 = FMath::FloorToInt((FMath::Min(A.X, B.X) - 25.0) / 16.0), X1 = FMath::FloorToInt((FMath::Max(A.X, B.X) + 25.0) / 16.0);
	const int32 Y0 = FMath::FloorToInt((FMath::Min(A.Y, B.Y) - 25.0) / 16.0), Y1 = FMath::FloorToInt((FMath::Max(A.Y, B.Y) + 25.0) / 16.0);
	for (int32 X = X0; X <= X1; ++X) for (int32 Y = Y0; Y <= Y1; ++Y)
	{
		const TArray<FVector4>* L = Crowns.Find((int64(X) << 32) ^ int64(uint32(Y))); if (!L) continue;
		for (const FVector4& S : *L)
		{
			const FVector C(S.X, S.Y, S.Z);
			if (FMath::PointDistToSegment(C, A, B) < S.W) return true;
		}
	}
	return false;
}

double ABruteCharacter::Floor(const FVector& P, double Up) const
{
	return bWorldReady ? World.GroundHeight(P.X, P.Y, P.Z + Up) : 0.0;
}

void ABruteCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	// input is polled every frame from the player controller (robust to lost Started/Completed events, see AWebTravCharacter round 19)
}

// ================================================================================================ input
FBruteInput ABruteCharacter::ReadInput(float Dt)
{
	FBruteInput I;
	if (bScript) { I = SampleScript(ScriptT); return I; }
	APlayerController* PC = Cast<APlayerController>(Controller);
	if (!PC) return I;
	auto K = [PC](const FKey& Key) { return PC->IsInputKeyDown(Key); };
	I.Move.Y = (K(EKeys::W) ? 1.f : 0.f) - (K(EKeys::S) ? 1.f : 0.f);
	I.Move.X = (K(EKeys::D) ? 1.f : 0.f) - (K(EKeys::A) ? 1.f : 0.f);
	const FVector2D Pad(PC->GetInputAnalogKeyState(EKeys::Gamepad_LeftX), PC->GetInputAnalogKeyState(EKeys::Gamepad_LeftY));
	if (Pad.Size() > 0.15f) I.Move = Pad;
	if (I.Move.Size() > 1.f) I.Move.Normalize();
	float Mx = 0.f, My = 0.f; PC->GetInputMouseDelta(Mx, My);
	float Sens = 1.f; if (IConsoleVariable* CV = IConsoleManager::Get().FindConsoleVariable(TEXT("wh.MouseSensitivity"))) Sens = FMath::Max(0.05f, CV->GetFloat());
	I.MouseDeg = FVector2D(Mx, My) * 0.14f * Sens;
	const FVector2D RS(PC->GetInputAnalogKeyState(EKeys::Gamepad_RightX), PC->GetInputAnalogKeyState(EKeys::Gamepad_RightY));
	if (RS.Size() > 0.15f) I.LookRate = FVector2D(RS.X * 160.f, RS.Y * 110.f);
	I.bJump = K(EKeys::SpaceBar) || K(EKeys::Gamepad_FaceButton_Bottom);
	I.bSprint = K(EKeys::LeftShift) || K(EKeys::Gamepad_LeftThumbstick) || PC->GetInputAnalogKeyState(EKeys::Gamepad_RightTriggerAxis) > 0.4f;
	I.bAttack = K(EKeys::LeftMouseButton) || K(EKeys::Gamepad_FaceButton_Left);
	I.bHeavy = K(EKeys::RightMouseButton) || K(EKeys::C) || K(EKeys::LeftControl) || K(EKeys::Gamepad_FaceButton_Top);
	I.bClap = K(EKeys::F) || K(EKeys::Gamepad_RightShoulder);
	I.bGrab = K(EKeys::E) || K(EKeys::Gamepad_FaceButton_Right);
	I.bDash = I.bSprint;
	return I;
}

void ABruteCharacter::LoadScript(const FString& Path)
{
	FString Txt; if (!FFileHelper::LoadFileToString(Txt, *Path)) { UE_LOG(LogWebHomage, Error, TEXT("WH_BRUTE script not found: %s"), *Path); return; }
	TSharedPtr<FJsonObject> Root; TSharedRef<TJsonReader<>> Rd = TJsonReaderFactory<>::Create(Txt);
	if (!FJsonSerializer::Deserialize(Rd, Root) || !Root.IsValid()) { UE_LOG(LogWebHomage, Error, TEXT("WH_BRUTE script parse error: %s"), *Path); return; }
	const TSharedPtr<FJsonObject>* Sp;
	if (Root->TryGetObjectField(TEXT("spawn"), Sp))
	{
		const TArray<TSharedPtr<FJsonValue>>* PA;
		if ((*Sp)->TryGetArrayField(TEXT("pos"), PA) && PA->Num() >= 3) { SpawnPos = FVector((*PA)[0]->AsNumber(), (*PA)[1]->AsNumber(), (*PA)[2]->AsNumber()); bHasSpawn = true; }
		(*Sp)->TryGetNumberField(TEXT("yaw"), SpawnYaw);
		double CP; if ((*Sp)->TryGetNumberField(TEXT("camPitch"), CP)) CamPitch = CP;
	}
	const TArray<TSharedPtr<FJsonValue>>* Keys;
	if (Root->TryGetArrayField(TEXT("keys"), Keys))
	{
		for (const TSharedPtr<FJsonValue>& V : *Keys)
		{
			const TSharedPtr<FJsonObject> O = V->AsObject(); if (!O) continue;
			FScriptKey K; K.T = O->GetNumberField(TEXT("t"));
			for (const auto& F : O->Values)
			{
				if (F.Key == TEXT("move")) { const TArray<TSharedPtr<FJsonValue>>& A = F.Value->AsArray(); if (A.Num() >= 2) { K.Move = FVector2D(A[0]->AsNumber(), A[1]->AsNumber()); K.bMove = true; } }
				else if (F.Key == TEXT("look")) { const TArray<TSharedPtr<FJsonValue>>& A = F.Value->AsArray(); if (A.Num() >= 2) { K.Look = FVector2D(A[0]->AsNumber(), A[1]->AsNumber()); K.bLook = true; } }
				else if (F.Key != TEXT("t")) { double D = 0; if (F.Value->TryGetNumber(D)) K.V.Add(FString(F.Key), (float)D); else { bool B = false; if (F.Value->TryGetBool(B)) K.V.Add(FString(F.Key), B ? 1.f : 0.f); } }
			}
			Script.Add(K);
		}
	}
	Script.Sort([](const FScriptKey& A, const FScriptKey& B) { return A.T < B.T; });
	bScript = Script.Num() > 0;
}

FBruteInput ABruteCharacter::SampleScript(double T) const
{
	FBruteInput I; TMap<FString, float> On;
	for (const FScriptKey& K : Script)
	{
		if (K.T > T) break;
		if (K.bMove) I.Move = K.Move;
		if (K.bLook) I.LookRate = K.Look;
		for (const auto& P : K.V) On.Add(P.Key, P.Value);
	}
	auto B = [&On](const TCHAR* N) { const float* V = On.Find(N); return V && *V > 0.5f; };
	I.bJump = B(TEXT("jump")); I.bSprint = B(TEXT("sprint")); I.bAttack = B(TEXT("attack")); I.bHeavy = B(TEXT("heavy"));
	I.bClap = B(TEXT("clap")); I.bGrab = B(TEXT("grab")); I.bDash = B(TEXT("dash")) || I.bSprint;
	return I;
}

FVector ABruteCharacter::WishDir(const FVector2D& Move) const
{
	const double Y = FMath::DegreesToRadians(CamYaw);
	const FVector F(FMath::Cos(Y), FMath::Sin(Y), 0.0), Rt(-FMath::Sin(Y), FMath::Cos(Y), 0.0);
	FVector W = F * Move.Y + Rt * Move.X;
	return W.SizeSquared() > 1.0 ? W.GetSafeNormal() : W;
}

// ================================================================================================ tick
void ABruteCharacter::Tick(float Dt)
{
	ACharacter::Tick(Dt);   // skip AWebHomageCharacter's auto-move demo
	Dt = FMath::Min(Dt, 1.f / 20.f);
	FBruteInput I = ReadInput(Dt);
	if (bScript) ScriptT += Dt;
	CamYaw += I.MouseDeg.X + I.LookRate.X * Dt;
	CamPitch = FMath::Clamp(CamPitch - I.MouseDeg.Y - I.LookRate.Y * Dt, -70.0, 45.0);
	LookIdle = (I.MouseDeg.SizeSquared() > 1e-4 || I.LookRate.SizeSquared() > 1.0) ? 0.0 : LookIdle + Dt;

	// fixed substeps (120 Hz) so fast falls never tunnel through a roof
	// press edges: Step sees them on the first substep only; UpdateAct sees this frame's edges against the frame start
	const FBruteInput FrameStart = Prev;
	const int32 N = FMath::Clamp(FMath::CeilToInt(Dt * 120.f), 1, 8);
	for (int32 K = 0; K < N; ++K) { Step(Dt / N, I); if (K == 0) Prev = I; }
	Prev = FrameStart;
	UpdateAct(Dt, I);
	Prev = I;

	SetActorLocationAndRotation(Pos * 100.0 + FVector(0, 0, GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), FRotator(0.0, FMath::RadiansToDegrees(Facing), 0.0));
	Animate(Dt);
	UpdateCamera(Dt);

	TelT += Dt; ++Frame;
	if (!CsvPath.IsEmpty())
	{
		static const TCHAR* ModeN[] = { TEXT("ground"), TEXT("air"), TEXT("wall"), TEXT("land") };
		static const TCHAR* ActN[] = { TEXT("none"), TEXT("punch"), TEXT("slap"), TEXT("clap"), TEXT("smash"), TEXT("slam"), TEXT("grab"), TEXT("throw"), TEXT("carry"), TEXT("uppercut") };
		CsvRows.Add(FString::Printf(TEXT("%.3f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%s,%s,%.2f,%d,%d,%d,%.2f,%.0f,%s"), TelT, Pos.X, Pos.Y, Pos.Z, Vel.X, Vel.Y, Vel.Z, H2(Vel).Size(),
			ModeN[(int32)Mode], ActN[(int32)Act], Charge, ChainN, DashesLeft, Held.IsValid() ? 1 : 0, ApexZ, BruteWorld::Collateral(), *LastEvent));
		LastEvent.Reset();
	}
}

void ABruteCharacter::Event(const FString& E)
{
	LastEvent = LastEvent.IsEmpty() ? E : LastEvent + TEXT("|") + E;
	UE_LOG(LogWebHomage, Display, TEXT("WH_BRUTE t=%.2f %s pos (%.1f %.1f %.1f) vel (%.1f %.1f %.1f)"), TelT, *E, Pos.X, Pos.Y, Pos.Z, Vel.X, Vel.Y, Vel.Z);
}

void ABruteCharacter::Step(float Dt, const FBruteInput& I)
{
	ModeT += Dt; DashT -= Dt; LandT -= Dt; ClapCd -= Dt; ComboWindow -= Dt; SprintKnockT -= Dt;
	const FVector Wish = WishDir(I.Move);
	if (Pos.Z < -60.0 || Pos.ContainsNaN())
	{	// fell through the world / into the river: back to the last street he stood on
		Pos = LastSafe + FVector(0, 0, 0.1); Vel = FVector::ZeroVector; bSlamDive = false; bCharging = false; SetMode(EBruteMode::Ground);
		Event(TEXT("rescue_to_last_safe"));
		return;
	}
	switch (Mode)
	{
	case EBruteMode::Ground: case EBruteMode::Land: StepGround(Dt, I, Wish); break;
	case EBruteMode::Air: StepAir(Dt, I, Wish); break;
	case EBruteMode::Wall: StepWall(Dt, I); break;
	}
}

void ABruteCharacter::StepGround(float Dt, const FBruteInput& I, const FVector& Wish)
{
	const bool bActing = Act != EBruteAct::None && Act != EBruteAct::Carry;
	const bool bLand = Mode == EBruteMode::Land;
	if (bLand && LandT <= 0.f) SetMode(EBruteMode::Ground);
	bSprinting = I.bSprint && I.Move.Size() > 0.3f && !bActing && !bCharging;
	double Target = I.Move.Size() < 0.05f ? 0.0 : (bSprinting ? SprintSpeed : (I.Move.Size() > 0.7f ? RunSpeed : WalkSpeed));
	if (bActing) Target *= 0.3; else if (Act == EBruteAct::Carry) Target = FMath::Min(Target, (double)RunSpeed * 0.85);
	if (bCharging) Target = H2(Vel).Size() > RunSpeed ? FMath::Max(Target * 0.35, H2(Vel).Size() * (1.0 - 0.35 * Dt)) : Target * 0.3;   // a sprinting charge keeps its momentum for a running super jump
	if (bLand) Target *= LandHard > 0.5f ? 0.0 : 0.4;
	const FVector Hv = H2(Vel);
	const FVector Want = Wish.GetSafeNormal() * Target;
	const double Acc = Target < Hv.Size() ? 55.0 : (bSprinting ? 30.0 : GroundAccel);
	FVector Dv = Want - Hv; const double M = Dv.Size(); if (M > Acc * Dt) Dv *= Acc * Dt / M;
	Vel.X += Dv.X; Vel.Y += Dv.Y; Vel.Z = 0.0;
	if (H2(Vel).Size() > 0.5)
	{
		const double WantYaw = FMath::Atan2(Vel.Y, Vel.X);
		const double Rate = bSprinting ? 7.0 : 11.0;
		Facing += FMath::FindDeltaAngleRadians(Facing, WantYaw) * (1.0 - FMath::Exp(-Rate * Dt));
	}
	else if (bActing || Held.IsValid())
	{	// stand and face where the camera looks while fighting / aiming a throw
		Facing += FMath::FindDeltaAngleRadians(Facing, FMath::DegreesToRadians(CamYaw)) * (1.0 - FMath::Exp(-8.0 * Dt));
	}

	// jump: tap = hop, hold = charge, release = super jump
	if (I.bJump && !Prev.bJump && !bActing && (!bLand || ModeT > 0.12)) { bCharging = true; Charge = 0.f; }
	if (bCharging)
	{
		if (I.bJump) Charge = FMath::Min(Charge + Dt, ChargeTime);
		else { bCharging = false; Launch(Charge < 0.16f ? -1.f : Charge / ChargeTime, Wish); return; }
	}

	FVector NP = Pos + H2(Vel) * Dt;
	FTravContact C;
	if (bWorldReady && World.PushOutCapsule(NP, R, H, StepH, C))
	{
		const FVector N2 = H2(C.Normal).GetSafeNormal();
		const FVector Into = Wish.IsNearlyZero() ? H2(Vel).GetSafeNormal() : Wish.GetSafeNormal();
		if (bSprinting && FVector::DotProduct(Into, -N2) > 0.55 && C.Top - NP.Z > 3.5 && Act == EBruteAct::None)
		{
			WallN = N2; WallTop = C.Top; Pos = NP; Vel = FVector(0, 0, WallClimbSpeed); Facing = FMath::Atan2(-N2.Y, -N2.X);
			SetMode(EBruteMode::Wall); Event(FString::Printf(TEXT("wall_run_start top=%.1f"), C.Top - NP.Z));
			return;
		}
		const double Vn = FVector::DotProduct(H2(Vel), N2); if (Vn < 0) Vel -= N2 * Vn;
		if (bSprinting && Vn < -12.0) { Impact(NP - N2 * 0.8 + FVector(0, 0, 1.2), 5.f, false, 0.6f, 14.f, 6.f); Trauma += 0.35; Event(TEXT("sprint_wall_bump")); }
	}
	const double G = Floor(NP, StepH + 0.05);
	if (G < NP.Z - StepH - 0.05)
	{	// walked off a ledge
		Pos = NP; SetMode(EBruteMode::Air); AirT = 0.0; ApexZ = Pos.Z; LaunchZ = Pos.Z; bCharging = false;
		return;
	}
	NP.Z = G; Pos = NP;
	if (G > -50.0) LastSafe = Pos;
	StepPhase += float(H2(Vel).Size() * Dt / 3.4 * 2.0 * PI);

	// sprinting knocks cars aside (a forward cone just ahead of the body)
	if (bSprinting && H2(Vel).Size() > 15.0 && SprintKnockT <= 0.f)
	{
		SprintKnockT = 0.07f;
		const FVector F(FMath::Cos(Facing), FMath::Sin(Facing), 0);
		const int32 Nk = BruteWorld::Blast(GetWorld(), (Pos + F * 1.6 + FVector(0, 0, 0.9)) * 100.0, 3.4f, 20.f, 9.f, F, 0.0f, nullptr);
		if (Nk) { Trauma += 0.12 * Nk; Event(FString::Printf(TEXT("sprint_knock %d"), Nk)); }
	}
}

void ABruteCharacter::Launch(float K, const FVector& Wish)
{
	const FVector Dir = Wish.SizeSquared() > 0.04 ? Wish.GetSafeNormal() : FVector(FMath::Cos(Facing), FMath::Sin(Facing), 0.0);
	const double Hs = H2(Vel).Size();
	if (K < 0.f)
	{
		Vel.Z = HopVz; Event(TEXT("hop"));
	}
	else
	{
		const double ChainK = (1.0 + 0.1 * FMath::Min(ChainN, 3)) * (Hs > RunSpeed + 2.0 ? 1.15 : 1.0);   // chains and sprint take-offs go even bigger
		const double Kk = FMath::Pow(FMath::Clamp((double)K, 0.0, 1.0), 0.8);
		const double Hgt = FMath::Lerp(7.0, (double)SuperJumpHeight, Kk) * ChainK;
		const double Vz = FMath::Sqrt(2.0 * Gravity * Hgt);
		const double Tflight = 2.0 * Vz / Gravity;
		const double Range = FMath::Lerp(10.0, (double)SuperJumpRange, Kk) * ChainK;
		const double Vh = FMath::Max(Range / Tflight, Hs * 0.9);
		Vel = Dir * Vh; Vel.Z = Vz;
		Facing = FMath::Atan2(Dir.Y, Dir.X);
		Trauma += 0.2 + 0.35 * K; FovKick += 6.0 + 10.0 * K;
		if (K > 0.45f) Impact(Pos, 4.f + 6.f * K, false, 0.5f + 0.6f * K, 10.f, 8.f);
		Event(FString::Printf(TEXT("super_jump k=%.2f chain=%d h=%.1f range=%.1f vz=%.1f vh=%.1f"), K, ChainN, Hgt, Range, Vz, Vh));
	}
	SetMode(EBruteMode::Air); AirT = 0.0; LaunchZ = Pos.Z; ApexZ = Pos.Z; DashesLeft = 2; Charge = 0.f;
	Pos.Z += 0.05;
}

void ABruteCharacter::StepAir(float Dt, const FBruteInput& I, const FVector& Wish)
{
	AirT += Dt;
	// air dash (sprint key pressed in the air)
	if (I.bDash && !Prev.bDash && DashesLeft > 0 && !bSlamDive)
	{
		const double Y = FMath::DegreesToRadians(CamYaw);
		const FVector Dir = Wish.SizeSquared() > 0.04 ? Wish.GetSafeNormal() : FVector(FMath::Cos(Y), FMath::Sin(Y), 0.0);
		const double Hs = FMath::Max((double)DashSpeed, H2(Vel).Size());
		Vel = Dir * Hs; Vel.Z = FMath::Max(Vel.Z, 5.0);
		Facing = FMath::Atan2(Dir.Y, Dir.X);
		--DashesLeft; DashT = 0.3f; FovKick += 9.0; Trauma += 0.18;
		Event(FString::Printf(TEXT("air_dash left=%d"), DashesLeft));
	}
	// grand slam dive (heavy in the air, high enough)
	if (I.bHeavy && !Prev.bHeavy && !bSlamDive && Pos.Z - Floor(Pos, 0.5) > 2.5 && !Held.IsValid())
	{
		bSlamDive = true; Act = EBruteAct::Slam; ActT = 0.f; ActDur = 99.f; bActHit = false;
		Vel.X *= 0.35; Vel.Y *= 0.35; Vel.Z = FMath::Min(Vel.Z, 4.0);
		Event(TEXT("grand_slam_dive"));
	}
	if (bSlamDive)
	{
		Vel.Z = FMath::Max(Vel.Z - 4.0 * Gravity * Dt, -(double)SlamSpeed);
	}
	else
	{
		Vel.Z -= Gravity * (DashT > 0.f ? 0.25 : (Vel.Z < 0 ? 1.15 : 1.0)) * Dt;
		Vel.Z = FMath::Max(Vel.Z, -75.0);
		const FVector Hv = H2(Vel); const double Cap = FMath::Max(Hv.Size(), 12.0);
		FVector Nv = Hv + Wish * AirAccel * Dt; if (Nv.Size() > Cap) Nv = Nv.GetSafeNormal() * Cap;
		Vel.X = Nv.X; Vel.Y = Nv.Y;
		if (H2(Vel).Size() > 3.0) Facing += FMath::FindDeltaAngleRadians(Facing, FMath::Atan2(Vel.Y, Vel.X)) * (1.0 - FMath::Exp(-4.0 * Dt));
	}
	FVector NP = Pos + Vel * Dt;
	FTravContact C;
	if (bWorldReady && World.PushOutCapsule(NP, R, H, 0.2, C))
	{
		const FVector N2 = H2(C.Normal).GetSafeNormal();
		const FVector Into = Wish.IsNearlyZero() ? H2(Vel).GetSafeNormal() : Wish.GetSafeNormal();
		if (!bSlamDive && (I.bSprint || bSprinting) && FVector::DotProduct(Into, -N2) > 0.4 && C.Top - NP.Z > 3.0 && Act == EBruteAct::None)
		{
			WallN = N2; WallTop = C.Top; Pos = NP; Vel = FVector(0, 0, FMath::Max((double)WallClimbSpeed, Vel.Z * 0.7)); Facing = FMath::Atan2(-N2.Y, -N2.X);
			SetMode(EBruteMode::Wall); Event(TEXT("wall_catch"));
			return;
		}
		const double Vn = FVector::DotProduct(H2(Vel), N2);
		if (Vn < -14.0) { Impact(NP - N2 * 0.8 + FVector(0, 0, 1.0), 6.f, false, 0.7f, 16.f, 6.f); Trauma += 0.4; Event(TEXT("air_wall_smash")); }
		if (Vn < 0) Vel -= N2 * Vn * 1.15;
	}
	ApexZ = FMath::Max(ApexZ, NP.Z);
	const double G = Floor(NP, FMath::Max(1.0, -Vel.Z * Dt + 0.5));
	if (Vel.Z <= 0.0 && NP.Z <= G)
	{
		NP.Z = G; Pos = NP;
		Land(-Vel.Z);
		return;
	}
	Pos = NP;
}

void ABruteCharacter::Land(double ImpactVz)
{
	const FVector F(FMath::Cos(Facing), FMath::Sin(Facing), 0);
	const double Drop = ApexZ - Pos.Z;
	if (bSlamDive)
	{
		bSlamDive = false; Act = EBruteAct::None;
		const float Rr = FMath::Clamp(14.f + float(Drop) * 0.35f, 16.f, 30.f);
		Impact(Pos, Rr, true, 1.5f, 34.f, 24.f);
		Trauma = 1.0; FovKick -= 8.0; LandT = 0.65f; LandHard = 1.f; Vel = FVector::ZeroVector;
		Event(FString::Printf(TEXT("grand_slam_impact r=%.1f drop=%.1f vz=%.1f"), Rr, Drop, ImpactVz));
		SetMode(EBruteMode::Land); ChainN = 0; DashesLeft = 2;
		return;
	}
	// leap chain: still holding jump on touchdown -> instant relaunch
	if (Prev.bJump && ImpactVz > 8.0 && ChainN < 6 && Act == EBruteAct::None)
	{
		++ChainN;
		if (ImpactVz > CraterVz) Impact(Pos, FMath::Clamp(float(ImpactVz) * 0.35f, 5.f, 14.f), true, 0.8f, 18.f, 12.f);
		Event(FString::Printf(TEXT("leap_chain n=%d vz=%.1f"), ChainN, ImpactVz));
		Launch(0.8f, H2(Vel).GetSafeNormal());
		return;
	}
	ChainN = 0; DashesLeft = 2;
	if (ImpactVz > CraterVz)
	{
		const float Rr = FMath::Clamp(float(ImpactVz) * 0.5f, 7.f, 22.f);
		Impact(Pos, Rr, true, FMath::Clamp(float(ImpactVz) / 30.f, 0.6f, 1.4f), 24.f, 16.f);
		Trauma = FMath::Max(Trauma, FMath::Clamp(ImpactVz / 35.0, 0.4, 1.0)); FovKick -= 5.0;
		LandT = 0.5f; LandHard = 1.f; Vel.X *= 0.35; Vel.Y *= 0.35;
		Event(FString::Printf(TEXT("crater_landing r=%.1f vz=%.1f drop=%.1f"), Rr, ImpactVz, Drop));
	}
	else if (ImpactVz > 9.0)
	{
		Impact(Pos, 4.5f, false, 0.4f, 8.f, 5.f);
		Trauma += 0.2; LandT = 0.2f; LandHard = 0.3f; Vel.X *= 0.8; Vel.Y *= 0.8;
		Event(FString::Printf(TEXT("landing vz=%.1f"), ImpactVz));
	}
	else { LandT = 0.f; LandHard = 0.f; }
	Vel.Z = 0.0;
	SetMode(LandT > 0.f ? EBruteMode::Land : EBruteMode::Ground);
}

void ABruteCharacter::StepWall(float Dt, const FBruteInput& I)
{
	// climb straight up the facade; leaving it at the roof edge pops the body over, Space kicks off, letting go of sprint + stick drops
	const FVector Along(-WallN.Y, WallN.X, 0.0);
	const double Lateral = FVector::DotProduct(WishDir(I.Move), Along) * 5.0;
	Vel = FVector(0, 0, WallClimbSpeed) + Along * Lateral;
	FVector NP = Pos + Vel * Dt - WallN * 0.6 * Dt;
	StepPhase += float(WallClimbSpeed * Dt / 2.6 * 2.0 * PI);
	FTravHit Hit;
	const bool bFace = bWorldReady && World.Raycast(NP + FVector(0, 0, 0.6), -WallN, R + 1.2, Hit);
	if (I.bJump && !Prev.bJump)
	{
		Vel = WallN * 15.0 + FVector(0, 0, 16.0); Facing = FMath::Atan2(WallN.Y, WallN.X);
		SetMode(EBruteMode::Air); AirT = 0; ApexZ = Pos.Z; DashesLeft = 2; Event(TEXT("wall_kick"));
		return;
	}
	if (!bFace)
	{	// over the top: momentum carries over the roof edge
		Vel = -WallN * 8.0 + FVector(0, 0, 11.0);
		SetMode(EBruteMode::Air); AirT = 0; ApexZ = Pos.Z; DashesLeft = 2; Pos = NP;
		Event(TEXT("wall_top_out"));
		return;
	}
	if ((!I.bSprint && I.Move.Y < 0.3f) || ModeT > 9.0)
	{
		Vel = WallN * 4.0; SetMode(EBruteMode::Air); AirT = 0; ApexZ = Pos.Z; Event(TEXT("wall_release"));
		return;
	}
	FTravContact C; if (bWorldReady) World.PushOutCapsule(NP, R, H, 0.2, C);
	Pos = NP;
}

// ================================================================================================ impacts & actions
void ABruteCharacter::Impact(const FVector& AtM, float RadiusM, bool bCrater, float Strength, float CarSpeed, float CarUp)
{
	UWorld* W = GetWorld(); if (!W) return;
	const double G = Floor(AtM, 1.5);
	const FVector At(AtM.X, AtM.Y, G > -900.0 ? G : AtM.Z);
	FActorSpawnParameters SP; SP.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	if (ABruteShockwave* S = W->SpawnActor<ABruteShockwave>(At * 100.0, FRotator::ZeroRotator, SP)) S->Init(RadiusM, bCrater, FVector::ZeroVector, Strength);
	const int32 Nc = BruteWorld::Blast(W, (At + FVector(0, 0, 0.8)) * 100.0, RadiusM, CarSpeed, CarUp, FVector::ZeroVector, -2.f, Held.Get());
	BruteWorld::Collateral() += (bCrater ? 25000.0 : 2500.0) * Strength;
	if (Nc) Event(FString::Printf(TEXT("blast_cars %d"), Nc));
}

void ABruteCharacter::StartAct(EBruteAct A)
{
	Act = A; ActT = 0.f; bActHit = false;
	switch (A)
	{
	case EBruteAct::Punch: ActDur = 0.42f; ActHitAt = 0.15f; break;
	case EBruteAct::Slap: ActDur = 0.55f; ActHitAt = 0.22f; break;
	case EBruteAct::Clap: ActDur = 0.72f; ActHitAt = 0.36f; ClapCd = 1.1f; break;
	case EBruteAct::Smash: ActDur = 0.9f; ActHitAt = 0.5f; break;
	case EBruteAct::Grab: ActDur = 0.4f; ActHitAt = 0.4f; break;
	case EBruteAct::Throw: ActDur = 0.5f; ActHitAt = 0.17f; break;
	case EBruteAct::Uppercut: ActDur = 0.6f; ActHitAt = 0.2f; break;
	default: ActDur = 0.f; ActHitAt = 0.f; break;
	}
	static const TCHAR* ActN[] = { TEXT("none"), TEXT("punch"), TEXT("slap"), TEXT("thunderclap"), TEXT("ground_smash"), TEXT("slam"), TEXT("grab"), TEXT("throw"), TEXT("carry"), TEXT("launcher_uppercut") };
	Event(FString::Printf(TEXT("act_%s"), ActN[(int32)A]));
}

void ABruteCharacter::UpdateAct(float Dt, const FBruteInput& I)
{
	const bool bGround = Mode == EBruteMode::Ground || Mode == EBruteMode::Land;
	const bool bFree = Act == EBruteAct::None || Act == EBruteAct::Carry;
	// new presses
	if (bFree && !bCharging)
	{
		if (Held.IsValid())
		{
			if ((I.bGrab && !Prev.bGrab) || (I.bAttack && !Prev.bAttack)) StartAct(EBruteAct::Throw);
		}
		else if (I.bGrab && !Prev.bGrab && bGround)
		{
			const FVector F(FMath::Cos(Facing), FMath::Sin(Facing), 0);
			// an existing physics car in reach first, else lift one out of traffic
			ABruteCar* Best = nullptr; double BestD = 6.0;
			for (TActorIterator<ABruteCar> It(GetWorld()); It; ++It)
			{
				const double D = FVector::Dist(It->GetActorLocation() / 100.0, Pos + F * 2.0 + FVector(0, 0, 0.8));
				if (D < BestD) { BestD = D; Best = *It; }
			}
			if (!Best)
			{
				TArray<ABruteCar*> Got; BruteWorld::TakeCars(GetWorld(), (Pos + F * 2.5 + FVector(0, 0, 0.8)) * 100.0, 6.0f, 1, Got);
				if (Got.Num()) Best = Got[0];
			}
			if (Best) { Held = Best; Best->SetHeld(true); StartAct(EBruteAct::Grab); }
			else Event(TEXT("grab_nothing"));
		}
		else if (I.bClap && !Prev.bClap && ClapCd <= 0.f && bGround) StartAct(EBruteAct::Clap);
		else if (I.bHeavy && !Prev.bHeavy && bGround) StartAct(EBruteAct::Smash);
		else if (I.bAttack && !Prev.bAttack && bGround && bSprinting && H2(Vel).Size() > RunSpeed) StartAct(EBruteAct::Uppercut);
		else if (I.bAttack && !Prev.bAttack)
		{
			Combo = ComboWindow > 0.f ? (Combo + 1) % 3 : 0;
			StartAct(Combo == 2 ? EBruteAct::Slap : EBruteAct::Punch);
		}
	}
	else if (Act == EBruteAct::Punch || Act == EBruteAct::Slap)
	{	// buffered combo press during the recovery
		if (I.bAttack && !Prev.bAttack && ActT > ActHitAt) { Combo = (Combo + 1) % 3; StartAct(Combo == 2 ? EBruteAct::Slap : EBruteAct::Punch); }
	}
	if (Act != EBruteAct::None && Act != EBruteAct::Carry && Act != EBruteAct::Slam)
	{
		ActT += Dt;
		if (!bActHit && ActT >= ActHitAt) { bActHit = true; DoHit(); }
		if (ActT >= ActDur)
		{
			if (Act == EBruteAct::Punch || Act == EBruteAct::Slap) ComboWindow = 0.45f;
			Act = Held.IsValid() ? EBruteAct::Carry : EBruteAct::None; ActT = 0.f;
		}
	}
	// the held car rides over the head (lifted in during Grab)
	if (ABruteCar* C = Held.Get())
	{
		const FVector F(FMath::Cos(Facing), FMath::Sin(Facing), 0);
		const FVector Over = Pos + FVector(0, 0, H + 0.55 + (C->bBig ? 1.5 : CarHalfH));
		FVector Target = Over; FRotator Rot(0.0, FMath::RadiansToDegrees(Facing) + 90.0, 0.0);
		if (Act == EBruteAct::Grab) { const float K = Smooth01(ActT / ActDur); Target = FMath::Lerp(Pos + F * 2.4 + FVector(0, 0, 0.9), Over, K); }
		if (Act == EBruteAct::Throw) { const float K = Smooth01(ActT / ActHitAt); Target = FMath::Lerp(Over, Over + F * 1.6 - FVector(0, 0, 0.6), K); }
		C->SetActorLocationAndRotation(Target * 100.0, FMath::RInterpTo(C->GetActorRotation(), Rot, Dt, 10.f));
	}
}

void ABruteCharacter::DoHit()
{
	UWorld* W = GetWorld(); if (!W) return;
	const FVector F(FMath::Cos(Facing), FMath::Sin(Facing), 0);
	FActorSpawnParameters SP; SP.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	switch (Act)
	{
	case EBruteAct::Punch:
	{
		const int32 N = BruteWorld::Blast(W, (Pos + F * 2.6 + FVector(0, 0, 1.2)) * 100.0, 3.6f, 30.f, 9.f, F, 0.15f, nullptr);
		if (ABruteShockwave* S = W->SpawnActor<ABruteShockwave>((Pos + F * 2.4) * 100.0, FRotator::ZeroRotator, SP)) S->Init(5.f, false, F, 0.4f);
		Trauma += N ? 0.35 : 0.12; Event(FString::Printf(TEXT("punch_hit cars=%d"), N));
		break;
	}
	case EBruteAct::Slap:
	{
		const FVector Side(-F.Y, F.X, 0);   // the backhand sweeps right to left... cars fly to the right side of the swing
		const int32 N = BruteWorld::Blast(W, (Pos + F * 2.2 + FVector(0, 0, 1.2)) * 100.0, 5.0f, 34.f, 7.f, F, -0.35f, nullptr);
		if (ABruteShockwave* S = W->SpawnActor<ABruteShockwave>((Pos + F * 2.0) * 100.0, FRotator::ZeroRotator, SP)) S->Init(7.f, false, (F + Side * 0.6).GetSafeNormal(), 0.5f);
		Trauma += N ? 0.45 : 0.18; Event(FString::Printf(TEXT("slap_hit cars=%d"), N));
		break;
	}
	case EBruteAct::Clap:
	{
		const int32 N = BruteWorld::Blast(W, (Pos + F * 1.5 + FVector(0, 0, 1.5)) * 100.0, 32.f, 42.f, 11.f, F, 0.62f, nullptr);
		if (ABruteShockwave* S = W->SpawnActor<ABruteShockwave>((Pos + F * 1.5) * 100.0, FRotator::ZeroRotator, SP)) S->Init(30.f, false, F, 1.f);
		Trauma = FMath::Max(Trauma, 0.7); FovKick -= 7.0; BruteWorld::Collateral() += 15000.0;
		Event(FString::Printf(TEXT("thunderclap cars=%d"), N));
		break;
	}
	case EBruteAct::Uppercut:
	{	// the launcher: everything in front goes straight up, the Brute pops off the ground with it
		const int32 N = BruteWorld::Blast(W, (Pos + F * 2.4 + FVector(0, 0, 0.6)) * 100.0, 5.5f, 9.f, 34.f, F, 0.0f, nullptr);
		if (ABruteShockwave* S = W->SpawnActor<ABruteShockwave>((Pos + F * 2.4) * 100.0, FRotator::ZeroRotator, SP)) S->Init(6.f, false, FVector::ZeroVector, 0.7f);
		if (Mode == EBruteMode::Ground || Mode == EBruteMode::Land) { Vel.Z = 9.0; Vel.X *= 0.4; Vel.Y *= 0.4; SetMode(EBruteMode::Air); AirT = 0; ApexZ = Pos.Z; LaunchZ = Pos.Z; Pos.Z += 0.05; }
		Trauma += N ? 0.5 : 0.2; FovKick += 5.0;
		Event(FString::Printf(TEXT("launcher_hit cars=%d"), N));
		break;
	}
	case EBruteAct::Smash:
		Impact(Pos + F * 2.4, 13.f, true, 1.1f, 26.f, 20.f);
		Trauma = FMath::Max(Trauma, 0.85); FovKick -= 5.0;
		Event(TEXT("ground_grand_slam"));
		break;
	case EBruteAct::Throw:
		if (ABruteCar* C = Held.Get())
		{
			const double Y = FMath::DegreesToRadians(CamYaw), Pt = FMath::DegreesToRadians(FMath::Clamp(-CamPitch + 6.0, -30.0, 50.0));
			const FVector Aim(FMath::Cos(Y) * FMath::Cos(Pt), FMath::Sin(Y) * FMath::Cos(Pt), FMath::Sin(Pt));
			Facing = Y;
			C->SetHeld(false);
			C->bThrown = true; C->ThrownT = 0.f;
			C->Launch((Aim * ThrowSpeed + H2(Vel)) * 100.0, FVector(FMath::FRandRange(-200.f, 200.f), FMath::FRandRange(-360.f, 360.f), FMath::FRandRange(-90.f, 90.f)));
			Held.Reset(); Trauma += 0.3; FovKick += 4.0;
			Event(FString::Printf(TEXT("throw speed=%.0f pitch=%.0f"), ThrowSpeed, FMath::RadiansToDegrees(Pt)));
		}
		break;
	default: break;
	}
}

// ================================================================================================ camera
void ABruteCharacter::UpdateCamera(float Dt)
{
	APlayerController* PC = Cast<APlayerController>(Controller);
	const double Spd = Vel.Size();
	double WantDist = 7.2 + FMath::Clamp((Spd - 8.0) / 30.0, 0.0, 1.0) * 3.0;
	if (Mode == EBruteMode::Air) WantDist += FMath::Clamp((Pos.Z - LaunchZ) / 30.0, 0.0, 1.0) * 2.0;
	if (Mode == EBruteMode::Wall) WantDist = 9.0;
	if (bCharging) WantDist += Charge / ChargeTime * 1.5;
	if (Held.IsValid()) WantDist += 2.0;
	CamDist = Approach(CamDist, WantDist, 3.0, Dt);
	FovKick = Approach(FovKick, 0.0, 2.5, Dt);
	const double WantFov = 70.0 + FMath::Clamp((Spd - 10.0) / 35.0, 0.0, 1.0) * 18.0 + FovKick;
	CamFov = Approach(CamFov, WantFov, 6.0, Dt);
	Trauma = FMath::Clamp(Trauma - Dt * 1.6, 0.0, 1.0);

	if (Mode == EBruteMode::Air && LookIdle > 0.8)
	{	// hands-off in a big jump: tilt down over the street so the landing zone is in view
		const double Hgt = Pos.Z - Floor(Pos, 0.5);
		CamPitch = Approach(CamPitch, -(12.0 + 18.0 * FMath::Clamp(Hgt / 40.0, 0.0, 1.0)), 1.6, Dt);
	}
	else if (Mode != EBruteMode::Air && LookIdle > 1.2 && CamPitch < -14.0) CamPitch = Approach(CamPitch, -12.0, 1.2, Dt);   // ease back after a jump
	double Pitch = CamPitch;
	if (Mode == EBruteMode::Wall) Pitch = FMath::Max(Pitch, 10.0);   // look up the facade
	const FRotator Rot(Pitch, CamYaw, 0.0);
	if (PC) PC->SetControlRotation(Rot);

	// collision: sweep from the pivot back along the view; the arm never passes through a facade
	double Arm = CamDist;
	if (bWorldReady)
	{
		const FVector Pivot = Pos + FVector(0, 0, 0.95 + 1.28);
		const FVector Back = -Rot.Vector();
		double Hd = 0; FVector Nn;
		if (World.SweepSolid(Pivot, Pivot + Back * (CamDist + 0.4), 0.35, Hd, Nn)) Arm = FMath::Max(1.6, Hd - 0.3);
		// tree crowns have no collision: shorten the arm until the lens is out of the leaves (and the line to the body is clear)
		auto Leaves = [this](const FVector& P0, const FVector& P1) { return SegHitsCrown(P0, P1) || World.SegmentHitsCrown(P0, P1); };
		if (Leaves(Pivot, Pivot + Back * (Arm + 0.6)))
		{
			double Lo = 3.2, Hi = Arm;   // leaves: never closer than 3.2 m (under a canopy the body would fill the screen)
			for (int32 K = 0; K < 6; ++K) { const double M = 0.5 * (Lo + Hi); if (Leaves(Pivot, Pivot + Back * (M + 0.6))) Hi = M; else Lo = M; }
			Arm = FMath::Min(Arm, FMath::Max(3.2, Lo));
		}
	}
	CameraBoom->TargetArmLength = float(Arm * 100.0);
	const double Sh = Trauma * Trauma;
	const double T = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
	FollowCamera->SetRelativeLocation(FVector(0.0, FMath::Sin(T * 47.0) * 22.0 * Sh, FMath::Sin(T * 53.0 + 1.3) * 18.0 * Sh));
	FollowCamera->SetRelativeRotation(FRotator(FMath::Sin(T * 41.0) * 2.5 * Sh, FMath::Sin(T * 37.0 + 0.7) * 2.5 * Sh, FMath::Sin(T * 29.0) * 3.0 * Sh));
	FollowCamera->SetFieldOfView(float(CamFov));
}

// ================================================================================================ rig
UStaticMeshComponent* ABruteCharacter::Part(USceneComponent* P, const TCHAR* N, UStaticMesh* M, const FVector& L, const FVector& S, UMaterialInstanceDynamic* Mat, const FRotator& Rot)
{
	UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this, N);
	C->SetupAttachment(P);
	C->SetStaticMesh(M);
	C->SetRelativeLocation(L); C->SetRelativeRotation(Rot); C->SetRelativeScale3D(S);
	C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	C->SetGenerateOverlapEvents(false);
	if (Mat) C->SetMaterial(0, Mat);
	C->RegisterComponent();
	Parts.Add(C);
	return C;
}

void ABruteCharacter::BuildRig()
{
	auto Joint = [this](USceneComponent* Parent, const TCHAR* N, const FVector& L)
	{
		USceneComponent* J = NewObject<USceneComponent>(this, N);
		J->SetupAttachment(Parent); J->SetRelativeLocation(L); J->RegisterComponent();
		return J;
	};
	// joint layout (cm, feet origin, X forward, Y right): Config/BruteRig.json when present (written by tools/brute/segment_brute.py)
	TMap<FString, FVector> J;
	J.Add(TEXT("Pelvis"), FVector(0, 0, 88)); J.Add(TEXT("Torso"), FVector(0, 0, 122)); J.Add(TEXT("Head"), FVector(3, 0, 209));
	J.Add(TEXT("UpperArm_L"), FVector(-10, -61, 191)); J.Add(TEXT("UpperArm_R"), FVector(-10, 61, 191));
	J.Add(TEXT("Forearm_L"), FVector(-5, -61, 137)); J.Add(TEXT("Forearm_R"), FVector(-5, 61, 137));
	J.Add(TEXT("Thigh_L"), FVector(0, -22, 83)); J.Add(TEXT("Thigh_R"), FVector(0, 22, 83));
	J.Add(TEXT("Shin_L"), FVector(0, -26, 36)); J.Add(TEXT("Shin_R"), FVector(0, 26, 36));
	{
		FString Txt; TSharedPtr<FJsonObject> Root;
		if (FFileHelper::LoadFileToString(Txt, *(FPaths::ProjectConfigDir() / TEXT("BruteRig.json"))) && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Txt), Root) && Root.IsValid())
		{
			const TSharedPtr<FJsonObject>* Js;
			if (Root->TryGetObjectField(TEXT("joints"), Js))
				for (const auto& KV : (*Js)->Values) { const TArray<TSharedPtr<FJsonValue>>& A = KV.Value->AsArray(); if (A.Num() >= 3) J.Add(FString(KV.Key), FVector(A[0]->AsNumber(), A[1]->AsNumber(), A[2]->AsNumber())); }
		}
	}
	const float Half = GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	Fig = Joint(GetCapsuleComponent(), TEXT("Brute_Fig"), FVector(0, 0, -Half));
	JHips = Joint(Fig, TEXT("Brute_Hips"), J[TEXT("Pelvis")]);
	JSpine = Joint(JHips, TEXT("Brute_Spine"), J[TEXT("Torso")] - J[TEXT("Pelvis")]);
	JHead = Joint(JSpine, TEXT("Brute_Head"), J[TEXT("Head")] - J[TEXT("Torso")]);
	const TCHAR* Sd[2] = { TEXT("L"), TEXT("R") };
	for (int32 S = 0; S < 2; ++S)
	{
		const FString U = FString(TEXT("UpperArm_")) + Sd[S], Fa = FString(TEXT("Forearm_")) + Sd[S], Th = FString(TEXT("Thigh_")) + Sd[S], Sh = FString(TEXT("Shin_")) + Sd[S];
		JSh[S] = Joint(JSpine, *(TEXT("Brute_Sh") + FString(Sd[S])), J[U] - J[TEXT("Torso")]);
		JEl[S] = Joint(JSh[S], *(TEXT("Brute_El") + FString(Sd[S])), J[Fa] - J[U]);
		JHip[S] = Joint(JHips, *(TEXT("Brute_Hip") + FString(Sd[S])), J[Th] - J[TEXT("Pelvis")]);
		JKn[S] = Joint(JHip[S], *(TEXT("Brute_Kn") + FString(Sd[S])), J[Sh] - J[Th]);
	}
	if (BuildRigFromMeshes()) return;

	// placeholder brick brute (engine cubes) until the Customuse body is imported (Scripts/build_brute.py)
	UStaticMesh* Cube = BruteFx::Cube(); UStaticMesh* Sph = BruteFx::Sphere();
	UMaterialInstanceDynamic* Skin = BruteFx::Mat(this, FLinearColor(0.10f, 0.32f, 0.06f));
	UMaterialInstanceDynamic* SkinD = BruteFx::Mat(this, FLinearColor(0.06f, 0.20f, 0.04f));
	UMaterialInstanceDynamic* Shorts = BruteFx::Mat(this, FLinearColor(0.22f, 0.04f, 0.30f));
	UMaterialInstanceDynamic* Hair = BruteFx::Mat(this, FLinearColor(0.015f, 0.012f, 0.01f));
	UMaterialInstanceDynamic* Eye = BruteFx::Mat(this, FLinearColor(0.9f, 0.9f, 0.85f), 0.3f);
	Part(JHips, TEXT("B_Pelvis"), Cube, FVector(0, 0, 0), FVector(0.62, 0.95, 0.42), Shorts);
	Part(JSpine, TEXT("B_Belly"), Cube, FVector(4, 0, 22), FVector(0.62, 0.90, 0.55), Skin);
	Part(JSpine, TEXT("B_Chest"), Cube, FVector(4, 0, 62), FVector(0.80, 1.28, 0.62), Skin);
	Part(JSpine, TEXT("B_Traps"), Cube, FVector(-6, 0, 86), FVector(0.55, 0.85, 0.24), SkinD);
	Part(JHead, TEXT("B_Neck"), Cube, FVector(0, 0, 4), FVector(0.30, 0.34, 0.18), SkinD);
	Part(JHead, TEXT("B_Skull"), Cube, FVector(4, 0, 24), FVector(0.38, 0.36, 0.40), Skin);
	Part(JHead, TEXT("B_Hair"), Cube, FVector(-2, 0, 45), FVector(0.42, 0.40, 0.12), Hair);
	Part(JHead, TEXT("B_HairBack"), Cube, FVector(-13, 0, 34), FVector(0.18, 0.38, 0.30), Hair);
	Part(JHead, TEXT("B_Brow"), Cube, FVector(23, 0, 31), FVector(0.07, 0.34, 0.06), SkinD);
	Part(JHead, TEXT("B_EyeL"), Cube, FVector(23, -8, 26), FVector(0.02, 0.07, 0.035), Eye);
	Part(JHead, TEXT("B_EyeR"), Cube, FVector(23, 8, 26), FVector(0.02, 0.07, 0.035), Eye);
	for (int32 S = 0; S < 2; ++S)
	{
		const double Side = S == 0 ? -1.0 : 1.0;
		Part(JSh[S], *(TEXT("B_Delt") + FString(Sd[S])), Sph, FVector(0, Side * 2, 2), FVector(0.55, 0.52, 0.50), Skin);
		Part(JSh[S], *(TEXT("B_Upper") + FString(Sd[S])), Cube, FVector(0, 0, -28), FVector(0.46, 0.46, 0.58), Skin);
		Part(JEl[S], *(TEXT("B_Fore") + FString(Sd[S])), Cube, FVector(0, 0, -24), FVector(0.52, 0.52, 0.52), Skin);
		Part(JEl[S], *(TEXT("B_Fist") + FString(Sd[S])), Cube, FVector(3, 0, -58), FVector(0.44, 0.42, 0.38), SkinD);
		Part(JHip[S], *(TEXT("B_Thigh") + FString(Sd[S])), Cube, FVector(0, 0, -22), FVector(0.48, 0.46, 0.50), Skin);
		Part(JHip[S], *(TEXT("B_Cuff") + FString(Sd[S])), Cube, FVector(0, 0, -6), FVector(0.52, 0.50, 0.26), Shorts);
		Part(JKn[S], *(TEXT("B_Shin") + FString(Sd[S])), Cube, FVector(0, 0, -16), FVector(0.40, 0.40, 0.40), Skin);
		Part(JKn[S], *(TEXT("B_Foot") + FString(Sd[S])), Cube, FVector(9, 0, -32), FVector(0.46, 0.30, 0.10), SkinD);
	}
	UE_LOG(LogWebHomage, Display, TEXT("WH_BRUTE rig: placeholder brick body (%d parts)"), Parts.Num());
}

bool ABruteCharacter::BuildRigFromMeshes()
{
	if (FParse::Param(FCommandLine::Get(), TEXT("WHBruteBricks"))) return false;
	struct FP { const TCHAR* Name; USceneComponent* J; };
	const FP List[] = { {TEXT("Pelvis"), JHips}, {TEXT("Torso"), JSpine}, {TEXT("Head"), JHead},
		{TEXT("UpperArm_L"), JSh[0]}, {TEXT("Forearm_L"), JEl[0]}, {TEXT("UpperArm_R"), JSh[1]}, {TEXT("Forearm_R"), JEl[1]},
		{TEXT("Thigh_L"), JHip[0]}, {TEXT("Shin_L"), JKn[0]}, {TEXT("Thigh_R"), JHip[1]}, {TEXT("Shin_R"), JKn[1]} };
	TArray<UStaticMesh*> Meshes;
	for (const FP& P : List)
	{
		UStaticMesh* M = LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("/Game/Brute/Parts/SM_Brute_%s.SM_Brute_%s"), P.Name, P.Name));
		if (!M) { UE_LOG(LogWebHomage, Display, TEXT("WH_BRUTE rig: /Game/Brute/Parts/SM_Brute_%s missing -> placeholder bricks"), P.Name); return false; }
		Meshes.Add(M);
	}
	for (int32 I = 0; I < Meshes.Num(); ++I)
	{
		UStaticMeshComponent* C = Part(List[I].J, *FString::Printf(TEXT("BM_%s"), List[I].Name), Meshes[I], FVector::ZeroVector, FVector::OneVector, nullptr);
		C->SetCastShadow(true);
	}
	UE_LOG(LogWebHomage, Display, TEXT("WH_BRUTE rig: Customuse body, %d parts"), Meshes.Num());
	return true;
}

FVector ABruteCharacter::HandWorldCm(int32 S) const
{
	return JEl[S] ? JEl[S]->GetComponentTransform().TransformPosition(FVector(0, 0, -58)) : GetActorLocation();
}

void ABruteCharacter::Animate(float Dt)
{
	FBrutePose T;
	const double Hs = H2(Vel).Size();
	float Rate = 14.f;
	if (Mode == EBruteMode::Ground || (Mode == EBruteMode::Land && LandT <= 0.f))
	{
		const float Amp = FMath::Clamp(float(Hs / RunSpeed), 0.f, 1.f) + (bSprinting ? FMath::Clamp(float((Hs - RunSpeed) / (SprintSpeed - RunSpeed)), 0.f, 1.f) * 0.7f : 0.f);
		const float Sp = FMath::Sin(StepPhase), Cp = FMath::Cos(StepPhase);
		const float Lean = 6.f + 14.f * FMath::Min(Amp, 1.f) + (bSprinting ? 22.f * FMath::Clamp(Amp - 1.f, 0.f, 1.f) / 0.7f : 0.f);
		T.SpinePitch = -Lean; T.HeadPitch = Lean * 0.6f; T.RootZ = -10.f * Amp * FMath::Abs(Cp) - 6.f * FMath::Min(Amp, 1.f);
		T.SpineYaw = 10.f * Amp * Sp; T.RootRoll = 3.f * Amp * Cp;
		for (int32 S = 0; S < 2; ++S)
		{
			const float Ph = S == 0 ? Sp : -Sp, Ph2 = S == 0 ? Cp : -Cp;
			T.HipPitch[S] = 34.f * Amp * Ph + Lean * 0.4f;
			T.Knee[S] = 12.f + 58.f * Amp * FMath::Max(0.f, Ph2) + 10.f * Amp;
			T.ShPitch[S] = -42.f * Amp * Ph + (bSprinting ? 10.f : 0.f);
			T.Elbow[S] = 25.f + 30.f * Amp;
			T.ShAbd[S] = 16.f + 6.f * Amp;
		}
		if (bCharging)
		{
			const float K = Smooth01(Charge / ChargeTime);
			T.RootZ = -60.f * K; T.SpinePitch = -18.f - 22.f * K; T.HeadPitch = 25.f * K;
			for (int32 S = 0; S < 2; ++S) { T.HipPitch[S] = 75.f * K; T.Knee[S] = 115.f * K; T.ShPitch[S] = -45.f * K; T.ShAbd[S] = 28.f; T.Elbow[S] = 35.f; T.HipAbd[S] = 10.f * K; }
			T.RootRoll = FMath::Sin(TelT * 40.0) * 1.5f * K;   // straining tremble
			Rate = 18.f;
		}
		if (Held.IsValid()) Rate = 12.f;
	}
	else if (Mode == EBruteMode::Land)
	{
		const float K = Smooth01(LandT / (LandHard > 0.5f ? 0.55f : 0.2f)) * FMath::Max(LandHard, 0.35f);
		T.RootZ = -80.f * K; T.SpinePitch = -50.f * K; T.HeadPitch = 35.f * K;
		T.HipPitch[0] = 85.f * K; T.Knee[0] = 125.f * K;          // kneeling left leg
		T.HipPitch[1] = 30.f * K; T.Knee[1] = 70.f * K; T.HipAbd[1] = 18.f * K;
		T.ShPitch[1] = 70.f * K; T.Elbow[1] = 8.f; T.ShAbd[1] = 14.f;    // right fist planted
		T.ShPitch[0] = -35.f * K; T.ShAbd[0] = 50.f * K; T.Elbow[0] = 35.f;
		Rate = 30.f;
	}
	else if (Mode == EBruteMode::Air)
	{
		if (bSlamDive)
		{
			T.SpinePitch = 8.f; T.HeadPitch = -5.f; T.RootPitch = -10.f;
			for (int32 S = 0; S < 2; ++S) { T.ShPitch[S] = 172.f; T.ShAbd[S] = 12.f; T.Elbow[S] = 30.f; T.HipPitch[S] = 55.f; T.Knee[S] = 95.f; }
			Rate = 20.f;
		}
		else if (DashT > 0.f)
		{
			T.SpinePitch = -42.f; T.HeadPitch = 30.f;
			for (int32 S = 0; S < 2; ++S) { T.ShPitch[S] = -55.f; T.ShAbd[S] = 25.f; T.Elbow[S] = 20.f; T.HipPitch[S] = -10.f + 40.f * S; T.Knee[S] = 60.f; }
			Rate = 20.f;
		}
		else if (Vel.Z > 2.0)
		{	// launch / rising: one knee driven up, fists thrown forward-up
			T.SpinePitch = -12.f; T.HeadPitch = 5.f;
			T.HipPitch[0] = 70.f; T.Knee[0] = 95.f; T.HipPitch[1] = -25.f; T.Knee[1] = 40.f;
			for (int32 S = 0; S < 2; ++S) { T.ShPitch[S] = 115.f; T.ShAbd[S] = 30.f; T.Elbow[S] = 45.f; }
		}
		else
		{	// falling: arms spread wide, legs bracing for the impact
			const float K = Smooth01(float(-Vel.Z / 25.0));
			T.SpinePitch = -5.f - 10.f * K; T.HeadPitch = 15.f * K;
			for (int32 S = 0; S < 2; ++S) { T.ShPitch[S] = 30.f + 20.f * K; T.ShAbd[S] = 65.f + 15.f * K; T.Elbow[S] = 30.f; T.HipPitch[S] = 25.f + 25.f * K; T.Knee[S] = 45.f + 40.f * K; T.HipAbd[S] = 12.f; }
		}
		Rate = FMath::Max(Rate, 10.f);
	}
	else if (Mode == EBruteMode::Wall)
	{
		const float Sp = FMath::Sin(StepPhase);
		T.SpinePitch = 6.f; T.HeadPitch = -30.f;
		for (int32 S = 0; S < 2; ++S)
		{
			const float Ph = S == 0 ? Sp : -Sp;
			T.ShPitch[S] = 150.f + 28.f * Ph; T.Elbow[S] = 45.f - 30.f * Ph; T.ShAbd[S] = 22.f;
			T.HipPitch[S] = 50.f - 35.f * Ph; T.Knee[S] = 70.f + 30.f * Ph;
		}
		Rate = 20.f;
	}

	// action overlays (arms / spine)
	const float A = ActDur > 0.f ? ActT : 0.f;
	auto Wind = [A](float HitAt) { return Smooth01(A / FMath::Max(HitAt, 0.01f)); };
	auto Strike = [A](float HitAt, float Len) { return EaseOut((A - HitAt) / Len); };
	switch (Act)
	{
	case EBruteAct::Punch:
	{
		const int32 S = (Combo % 2 == 0) ? 0 : 1; const float Sg = S == 0 ? 1.f : -1.f;
		if (A < ActHitAt) { const float K = Wind(ActHitAt); T.ShPitch[S] = FMath::Lerp(T.ShPitch[S], -30.f, K); T.Elbow[S] = 115.f; T.SpineYaw = 22.f * Sg * K; T.ShAbd[S] = 20.f; }
		else { const float K = Strike(ActHitAt, 0.07f); T.ShPitch[S] = FMath::Lerp(-30.f, 90.f, K); T.Elbow[S] = FMath::Lerp(115.f, 4.f, K); T.ShAbd[S] = 6.f; T.ShYaw[S] = -8.f * Sg; T.SpineYaw = -26.f * Sg; T.SpinePitch -= 10.f; }
		T.ShPitch[1 - S] = 40.f; T.Elbow[1 - S] = 100.f; T.ShAbd[1 - S] = 18.f;   // guard
		Rate = 34.f; break;
	}
	case EBruteAct::Slap:
	{
		if (A < ActHitAt) { const float K = Wind(ActHitAt); T.ShPitch[1] = 85.f * K; T.ShYaw[1] = -75.f * K; T.Elbow[1] = 45.f; T.ShAbd[1] = 8.f; T.SpineYaw = 32.f * K; }
		else { const float K = Strike(ActHitAt, 0.11f); T.ShPitch[1] = 82.f; T.ShYaw[1] = FMath::Lerp(-75.f, 80.f, K); T.Elbow[1] = FMath::Lerp(45.f, 6.f, K); T.ShAbd[1] = 8.f; T.SpineYaw = FMath::Lerp(32.f, -32.f, K); }
		T.ShPitch[0] = 25.f; T.ShAbd[0] = 35.f; T.Elbow[0] = 60.f;
		Rate = 34.f; break;
	}
	case EBruteAct::Clap:
	{
		const float Out = A < ActHitAt ? Wind(ActHitAt) : 1.f, In = A < ActHitAt ? 0.f : Strike(ActHitAt, 0.06f);
		for (int32 S = 0; S < 2; ++S)
		{
			const float Sg = S == 0 ? -1.f : 1.f;
			T.ShPitch[S] = 85.f * Out; T.ShYaw[S] = Sg * FMath::Lerp(88.f * Out, 7.f, In); T.Elbow[S] = FMath::Lerp(20.f, 12.f, In); T.ShAbd[S] = 6.f;
		}
		T.SpinePitch = FMath::Lerp(12.f * Out, -18.f, In); T.HeadPitch = FMath::Lerp(-10.f * Out, 12.f, In); T.RootZ = FMath::Lerp(6.f * Out, -18.f, In);
		Rate = 36.f; break;
	}
	case EBruteAct::Smash:
	{
		if (A < ActHitAt) { const float K = Wind(ActHitAt); for (int32 S = 0; S < 2; ++S) { T.ShPitch[S] = 175.f * K; T.Elbow[S] = 35.f; T.ShAbd[S] = 10.f; } T.SpinePitch = 14.f * K; T.RootZ = 12.f * K; T.HeadPitch = -12.f * K; }
		else
		{
			const float K = Strike(ActHitAt, 0.08f);
			for (int32 S = 0; S < 2; ++S) { T.ShPitch[S] = FMath::Lerp(175.f, 55.f, K); T.Elbow[S] = FMath::Lerp(35.f, 2.f, K); T.ShAbd[S] = 10.f; T.HipPitch[S] = 55.f * K; T.Knee[S] = 85.f * K; }
			T.SpinePitch = FMath::Lerp(14.f, -55.f, K); T.RootZ = FMath::Lerp(12.f, -55.f, K); T.HeadPitch = 30.f * K;
		}
		Rate = 36.f; break;
	}
	case EBruteAct::Uppercut:
	{	// right fist from the knee to the sky, whole body rising into it
		const float K = A < ActHitAt ? Wind(ActHitAt) : 1.f, Up = A < ActHitAt ? 0.f : Strike(ActHitAt, 0.09f);
		T.ShPitch[1] = FMath::Lerp(-25.f * K, 168.f, Up); T.Elbow[1] = FMath::Lerp(95.f, 18.f, Up); T.ShAbd[1] = 10.f;
		T.ShPitch[0] = FMath::Lerp(20.f, -35.f, Up); T.Elbow[0] = 70.f; T.ShAbd[0] = 30.f;
		T.SpinePitch = FMath::Lerp(-35.f * K, 18.f, Up); T.SpineYaw = FMath::Lerp(25.f * K, -20.f, Up); T.HeadPitch = FMath::Lerp(20.f * K, -25.f, Up);
		T.RootZ = FMath::Lerp(-35.f * K, 8.f, Up);
		for (int32 S = 0; S < 2; ++S) { T.HipPitch[S] = FMath::Lerp(55.f * K, 5.f, Up); T.Knee[S] = FMath::Lerp(80.f * K, 10.f, Up); }
		Rate = 36.f; break;
	}
	case EBruteAct::Grab:
	{
		const float K = Smooth01(A / ActDur);
		for (int32 S = 0; S < 2; ++S) { T.ShPitch[S] = FMath::Lerp(55.f, 168.f, K); T.Elbow[S] = FMath::Lerp(15.f, 28.f, K); T.ShAbd[S] = 24.f; }
		T.SpinePitch = FMath::Lerp(-30.f, 4.f, K); T.RootZ = FMath::Lerp(-35.f, 0.f, K);
		Rate = 28.f; break;
	}
	case EBruteAct::Carry:
		for (int32 S = 0; S < 2; ++S) { T.ShPitch[S] = 168.f; T.Elbow[S] = 26.f; T.ShAbd[S] = 24.f; }
		T.SpinePitch = FMath::Min(T.SpinePitch, 0.f) + 4.f; T.HeadPitch = -6.f;
		break;
	case EBruteAct::Throw:
	{
		const float K = A < ActHitAt ? Smooth01(A / ActHitAt) : 1.f;
		for (int32 S = 0; S < 2; ++S) { T.ShPitch[S] = FMath::Lerp(170.f, 45.f, K); T.Elbow[S] = FMath::Lerp(25.f, 5.f, K); T.ShAbd[S] = 20.f; }
		T.SpinePitch = FMath::Lerp(10.f, -35.f, K); T.HipPitch[0] = 30.f * K; T.Knee[0] = 40.f * K;
		Rate = 36.f; break;
	}
	default: break;
	}
	Pose.Blend(T, 1.f - FMath::Exp(-Rate * Dt));
	ApplyPose();
}

void ABruteCharacter::ApplyPose()
{
	if (!Fig) return;
	const float Half = GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	Fig->SetRelativeLocationAndRotation(FVector(0, 0, -Half + Pose.RootZ), FRotator(Pose.RootPitch, 0, Pose.RootRoll));
	JSpine->SetRelativeRotation(FRotator(Pose.SpinePitch, Pose.SpineYaw, Pose.SpineRoll));
	JHead->SetRelativeRotation(FRotator(Pose.HeadPitch, 0, 0));
	for (int32 S = 0; S < 2; ++S)
	{
		// UE roll: + swings a hanging limb toward -Y, so abduction (outward) is -roll on the right side (+Y) and +roll on the left
		const float Out = S == 0 ? 1.f : -1.f;
		JSh[S]->SetRelativeRotation(FRotator(Pose.ShPitch[S], Pose.ShYaw[S], Pose.ShAbd[S] * Out));
		JEl[S]->SetRelativeRotation(FRotator(Pose.Elbow[S], 0, 0));
		JHip[S]->SetRelativeRotation(FRotator(Pose.HipPitch[S], 0, Pose.HipAbd[S] * Out));
		JKn[S]->SetRelativeRotation(FRotator(-Pose.Knee[S], 0, 0));
	}
}
