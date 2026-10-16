// Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
#include "Brute/BruteHUD.h"
#include "Brute/BruteCharacter.h"
#include "Brute/BruteFx.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void ABruteHUD::BeginPlay()
{
	Super::BeginPlay();
	bOff = FParse::Param(FCommandLine::Get(), TEXT("WHNoHud"));
}

void ABruteHUD::DrawHUD()
{
	Super::DrawHUD();
	if (bOff || !Canvas) return;
	const float Dt = GetWorld() ? GetWorld()->GetDeltaSeconds() : 0.016f;
	T += Dt;
	APlayerController* PC = GetOwningPlayerController();
	if (PC)
	{
		const bool bH = PC->IsInputKeyDown(EKeys::H) || PC->IsInputKeyDown(EKeys::Gamepad_Special_Left);
		if (bH && !bHWas) bCard = !bCard;
		bHWas = bH;
	}
	const float S = Canvas->ClipY / 1080.f;
	UFont* Big = GEngine->GetLargeFont(); UFont* Small = GEngine->GetSmallFont();

	// collateral counter: rolls up toward the real total
	const double Real = BruteWorld::Collateral();
	ShownCollateral += (Real - ShownCollateral) * FMath::Min(1.0, Dt * 4.0);
	if (Real - ShownCollateral < 1.0) ShownCollateral = Real;
	const FString Money = TEXT("$") + FText::AsNumber(FMath::RoundToInt64(ShownCollateral)).ToString();
	float W = 0, H = 0; Canvas->StrLen(Big, Money, W, H);
	const float Scale = 2.2f * S;
	const float X = Canvas->ClipX - W * Scale - 40.f * S, Y = 30.f * S;
	DrawText(TEXT("COLLATERAL DAMAGE"), FLinearColor(0.75f, 0.95f, 0.6f, 0.85f), Canvas->ClipX - 250.f * S, Y, Small, 1.4f * S);
	DrawText(Money, FLinearColor(0.f, 0.f, 0.f, 0.6f), X + 3.f * S, Y + 25.f * S, Big, Scale);
	DrawText(Money, FLinearColor(0.55f, 1.f, 0.35f, 1.f), X, Y + 22.f * S, Big, Scale);

	if (const ABruteCharacter* B = PC ? Cast<ABruteCharacter>(PC->GetPawn()) : nullptr)
	{
		if (B->IsCharging())
		{	// super-jump charge meter under the body
			const float K = B->GetCharge01();
			const float BW = 300.f * S, BH = 14.f * S, BX = Canvas->ClipX * 0.5f - BW * 0.5f, BY = Canvas->ClipY * 0.80f;
			DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.5f), BX - 3.f * S, BY - 3.f * S, BW + 6.f * S, BH + 6.f * S);
			DrawRect(K >= 0.999f ? FLinearColor(1.f, 0.85f, 0.2f, 0.95f) : FLinearColor(0.35f, 0.9f, 0.25f, 0.9f), BX, BY, BW * K, BH);
			DrawText(K >= 0.999f ? TEXT("FULL POWER") : TEXT("SUPER JUMP"), FLinearColor::White, BX, BY - 26.f * S, Small, 1.3f * S);
		}
	}

	if (bCard)   // owner 2026-10-16: the controls stay on screen (bottom left) for the whole session; H still hides / shows them
	{
		static const TCHAR* Lines[] = {
			TEXT("WASD move   Mouse look   Shift sprint (knocks cars aside)"),
			TEXT("Space hop   HOLD Space = charge SUPER JUMP   keep holding on landing = leap chain"),
			TEXT("In the air: Shift air dash   RMB / C = GRAND SLAM dive"),
			TEXT("Sprint into a building = run up the wall   In the air at a wall: LMB = punch in & hang, W / Shift climb, S drop, Space kick off"),
			TEXT("LMB punch, punch, SLAP   Sprint + LMB = LAUNCHER   RMB / C = ground smash   F = THUNDERCLAP"),
			TEXT("E grab a car   E / LMB throw it where you look      Hold R = back to the street (if stuck)"),
			TEXT("Pad: A jump  X attack  Y slam  B grab/throw  R1 clap  R2 sprint/dash      H hide / show"),
		};
		const float A = 1.f;
		const float LX = 36.f * S, LH = 24.f * S, N = UE_ARRAY_COUNT(Lines);
		const float LY = Canvas->ClipY - 40.f * S - LH * N;
		DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.45f * A), LX - 14.f * S, LY - 14.f * S, 900.f * S, LH * N + 24.f * S);
		for (int32 I = 0; I < N; ++I) DrawText(Lines[I], FLinearColor(1.f, 1.f, 1.f, A), LX, LY + I * LH, Small, 1.25f * S);
	}
}
