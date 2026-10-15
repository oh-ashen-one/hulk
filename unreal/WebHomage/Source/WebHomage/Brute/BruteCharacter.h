// Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
// Brute: the playable green brawler (~2.6 m). Replaces the web-swinging hero as the default pawn (AWebTravGameMode; -WHSpidey restores it).
//
// Movement is its own kinematic body in METRES on the traversal's proven world queries (FWebTravWorld: GroundHeight, PushOutCapsule,
// SweepSolid) -- CharacterMovement is switched off, as the swing hero does, because the city's raw collision has invisible floors/walls.
//   ground: walk / run / sprint (Shift: faster than traffic, cars in the path are knocked aside)
//   jump:   tap Space = hop; HOLD Space = charge (crouch) -> release = SUPER JUMP up to ~40 m high / ~100 m long (along the stick / camera)
//           hold Space through a landing = LEAP CHAIN (instant re-launch, +10 % per link)
//   air:    Shift = air dash (2 per jump), RMB / C = GRAND SLAM dive -> crater shockwave on landing
//   wall:   sprint into a facade = run straight up it, momentum pops over the roof edge; Space on the wall = kick off
//   land:   hard landings crater the street, shake the camera and blast cars outward
//   combat: LMB = punch, punch, SLAP combo; RMB / C on the ground = overhead GRAND SLAM smash; F = THUNDERCLAP (forward cone);
//           E = grab the nearest car (lift overhead) / E or LMB while holding = THROW it where the camera looks
// Pad: A jump, X attack, Y slam, B grab/throw, R1 clap, L3 / R2 sprint+dash, sticks move / look.
//
// Automation: -WHBruteScript=<json> replays timed inputs ({"spawn":{"pos":[x,y,z],"yaw":deg},"keys":[{"t":0,"move":[x,y],"sprint":0,
// "jump":0,"attack":0,"heavy":0,"clap":0,"grab":0,"dash":0,"look":[yawDegPerSec,pitchDegPerSec]}]}), -WHBruteCsv=<csv> writes telemetry.
#pragma once

#include "CoreMinimal.h"
#include "Core/WebHomageCharacter.h"
#include "Traversal/WebTravWorld.h"
#include "BruteCharacter.generated.h"

class UStaticMeshComponent;
class USceneComponent;
class UMaterialInstanceDynamic;
class ABruteCar;

UENUM()
enum class EBruteMode : uint8 { Ground, Air, Wall, Land };

UENUM()
enum class EBruteAct : uint8 { None, Punch, Slap, Clap, Smash, Slam, Grab, Throw, Carry };

struct FBruteInput
{
	FVector2D Move = FVector2D::ZeroVector;   // x right, y forward (stick)
	FVector2D LookRate = FVector2D::ZeroVector; // deg/s (scripted / pad)
	FVector2D MouseDeg = FVector2D::ZeroVector; // deg this frame (mouse)
	bool bJump = false, bSprint = false, bAttack = false, bHeavy = false, bClap = false, bGrab = false, bDash = false;
};

/** Joint angles (deg) and root offsets of the procedural rig. */
struct FBrutePose
{
	float RootZ = 0, RootPitch = 0, RootRoll = 0;
	float SpinePitch = 0, SpineYaw = 0, SpineRoll = 0, HeadPitch = 0;
	float ShPitch[2] = { 0, 0 }, ShAbd[2] = { 12, 12 }, ShYaw[2] = { 0, 0 }, Elbow[2] = { 15, 15 };
	float HipPitch[2] = { 0, 0 }, HipAbd[2] = { 4, 4 }, Knee[2] = { 5, 5 };
	void Blend(const FBrutePose& T, float A);
};

UCLASS(config=Game)
class WEBHOMAGE_API ABruteCharacter : public AWebHomageCharacter
{
	GENERATED_BODY()

public:
	ABruteCharacter();
	virtual void Tick(float Dt) override;

	// ---- tuning (metres, seconds; -WHBruteTune=Name=V,... overrides a few)
	UPROPERTY(Config, EditAnywhere, Category="Brute") float Gravity = 22.f;
	UPROPERTY(Config, EditAnywhere, Category="Brute") float WalkSpeed = 7.f;
	UPROPERTY(Config, EditAnywhere, Category="Brute") float RunSpeed = 13.f;
	UPROPERTY(Config, EditAnywhere, Category="Brute") float SprintSpeed = 27.f;
	UPROPERTY(Config, EditAnywhere, Category="Brute") float GroundAccel = 38.f;
	UPROPERTY(Config, EditAnywhere, Category="Brute") float AirAccel = 7.f;
	UPROPERTY(Config, EditAnywhere, Category="Brute") float HopVz = 13.f;
	UPROPERTY(Config, EditAnywhere, Category="Brute") float ChargeTime = 0.85f;
	UPROPERTY(Config, EditAnywhere, Category="Brute") float SuperJumpHeight = 40.f;   // apex at full charge (m)
	UPROPERTY(Config, EditAnywhere, Category="Brute") float SuperJumpRange = 100.f;   // ground distance at full charge (m, flat)
	UPROPERTY(Config, EditAnywhere, Category="Brute") float DashSpeed = 24.f;
	UPROPERTY(Config, EditAnywhere, Category="Brute") float WallClimbSpeed = 18.f;
	UPROPERTY(Config, EditAnywhere, Category="Brute") float SlamSpeed = 60.f;
	UPROPERTY(Config, EditAnywhere, Category="Brute") float ThrowSpeed = 58.f;
	UPROPERTY(Config, EditAnywhere, Category="Brute") float CraterVz = 17.f;          // landing speed that cracks the street

	EBruteMode GetMode() const { return Mode; }
	bool IsCharging() const { return bCharging && Charge > 0.12f; }
	float GetCharge01() const { return FMath::Clamp(Charge / ChargeTime, 0.f, 1.f); }
	FVector GetPosM() const { return Pos; }
	FVector GetVelM() const { return Vel; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

private:
	// ---- world
	FWebTravWorld World;
	bool bWorldReady = false;
	FDelegateHandle LevelAddedHandle, LevelRemovedHandle;
	void OnLevelAdded(ULevel* L, UWorld* W);
	void OnLevelRemoved(ULevel* L, UWorld* W);
	double Floor(const FVector& P, double Up = 1.2) const;

	// ---- body state (m, m/s); Pos = feet
	FVector Pos = FVector::ZeroVector, Vel = FVector::ZeroVector;
	double Facing = 0.0;                // rad
	EBruteMode Mode = EBruteMode::Air;
	double ModeT = 0.0, AirT = 0.0, ApexZ = 0.0, LaunchZ = 0.0;
	float Charge = 0.f; bool bCharging = false, bJumpWas = false, bChainArmed = false;
	int32 ChainN = 0, DashesLeft = 2;
	float DashT = 0.f, LandT = 0.f, LandHard = 0.f, SprintKnockT = 0.f, StepPhase = 0.f;
	bool bSlamDive = false, bSprinting = false;
	FVector WallN = FVector::ForwardVector; double WallTop = 0.0;
	static constexpr double R = 0.75, H = 2.55, StepH = 0.7;

	// ---- actions
	EBruteAct Act = EBruteAct::None;
	float ActT = 0.f, ActDur = 0.f, ActHitAt = 0.f; bool bActHit = false;
	int32 Combo = 0; float ComboWindow = 0.f, ClapCd = 0.f;
	TWeakObjectPtr<ABruteCar> Held;
	FBruteInput Prev;
	void StartAct(EBruteAct A);
	void UpdateAct(float Dt, const FBruteInput& I);
	void DoHit();

	// ---- sim
	void Step(float Dt, const FBruteInput& I);
	void StepGround(float Dt, const FBruteInput& I, const FVector& Wish);
	void StepAir(float Dt, const FBruteInput& I, const FVector& Wish);
	void StepWall(float Dt, const FBruteInput& I);
	void Launch(float K, const FVector& Wish);
	void Land(double ImpactVz);
	void Impact(const FVector& AtM, float RadiusM, bool bCrater, float Strength, float CarSpeed, float CarUp);
	FVector WishDir(const FVector2D& Move) const;
	void SetMode(EBruteMode M) { Mode = M; ModeT = 0.0; }

	// ---- input
	FBruteInput ReadInput(float Dt);
	struct FScriptKey { float T = 0; TMap<FString, float> V; FVector2D Move = FVector2D::ZeroVector, Look = FVector2D::ZeroVector; bool bMove = false, bLook = false; };
	TArray<FScriptKey> Script; bool bScript = false; double ScriptT = 0.0;
	FVector SpawnPos = FVector::ZeroVector; double SpawnYaw = 0.0; bool bHasSpawn = false;
	void LoadScript(const FString& Path);
	FBruteInput SampleScript(double T) const;

	// ---- camera (control rotation drives yaw / pitch; own collision + speed FOV + trauma shake)
	double CamYaw = 0.0, CamPitch = -12.0, CamDist = 7.5, CamFov = 72.0, Trauma = 0.0, FovKick = 0.0, LookIdle = 0.0;
	void UpdateCamera(float Dt);

	// ---- rig
	UPROPERTY(Transient) TObjectPtr<USceneComponent> Fig;
	UPROPERTY(Transient) TObjectPtr<USceneComponent> JHips;
	UPROPERTY(Transient) TObjectPtr<USceneComponent> JSpine;
	UPROPERTY(Transient) TObjectPtr<USceneComponent> JHead;
	UPROPERTY(Transient) TObjectPtr<USceneComponent> JSh[2];
	UPROPERTY(Transient) TObjectPtr<USceneComponent> JEl[2];
	UPROPERTY(Transient) TObjectPtr<USceneComponent> JHip[2];
	UPROPERTY(Transient) TObjectPtr<USceneComponent> JKn[2];
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Parts;
	FBrutePose Pose;
	void BuildRig();
	bool BuildRigFromMeshes();
	UStaticMeshComponent* Part(USceneComponent* P, const TCHAR* N, class UStaticMesh* M, const FVector& L, const FVector& S, UMaterialInstanceDynamic* Mat, const FRotator& Rot = FRotator::ZeroRotator);
	void Animate(float Dt);
	void ApplyPose();
	FVector HandWorldCm(int32 S) const;

	// ---- telemetry
	FString CsvPath; TArray<FString> CsvRows; double TelT = 0.0; int64 Frame = 0;
	FString LastEvent;
	void Event(const FString& E);
};
