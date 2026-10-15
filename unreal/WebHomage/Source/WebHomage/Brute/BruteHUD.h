// Hulk-in-Manhattan fan homage. Not affiliated with Marvel, Disney, Radical Entertainment, Vivendi, Activision or Sierra.
// Brute HUD: collateral damage counter (top right), super-jump charge meter, and a controls card (first 25 s; H toggles). -WHNoHud hides it.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "BruteHUD.generated.h"

UCLASS()
class WEBHOMAGE_API ABruteHUD : public AHUD
{
	GENERATED_BODY()
public:
	virtual void BeginPlay() override;
	virtual void DrawHUD() override;
private:
	bool bOff = false, bCard = true, bHWas = false;
	double ShownCollateral = 0.0;
	float T = 0.f;
};
