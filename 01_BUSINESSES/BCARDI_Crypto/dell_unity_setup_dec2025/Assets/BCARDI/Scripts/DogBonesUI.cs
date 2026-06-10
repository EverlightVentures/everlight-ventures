using UnityEngine;
using UnityEngine.UI;

namespace BCARDI
{
    public sealed class DogBonesUI : MonoBehaviour
    {
        public EnergySystem Energy;
        public Text BonesText;

        private void Update()
        {
            if (Energy == null || BonesText == null) return;
            BonesText.text = "Dog Bones: " + Energy.CurrentBones + "/" + Energy.MaxBones;
        }
    }
}
