
using UnityEngine;
using ArenaAdvance.Gameplay;

namespace ArenaAdvance.Managers
{
    public class UnitBehaviour : MonoBehaviour
    {
        [Header("Visual References")]
        [SerializeField] private SpriteRenderer spriteRenderer;
        [SerializeField] private Animator animator;
        [SerializeField] private Transform healthBarPivot;
        [SerializeField] private SpriteRenderer healthBarFill;
        [SerializeField] private ParticleSystem hitEffect;
        [SerializeField] private ParticleSystem deathEffect;

        [Header("Settings")]
        [SerializeField] private Color playerColor = Color.blue;
        [SerializeField] private Color opponentColor = Color.red;

        private BattleUnit unitData;
        private int lastHealth;

        public BattleUnit Data => unitData;

        public void Initialize(BattleUnit data)
        {
            unitData = data;
            lastHealth = data.currentHealth;

            // Set team color
            if (spriteRenderer != null)
            {
                spriteRenderer.color = data.ownerId == 0 ? playerColor : opponentColor;
            }

            // Face the correct direction
            if (data.ownerId == 0)
            {
                // Player units face up
                transform.rotation = Quaternion.identity;
            }
            else
            {
                // Opponent units face down
                transform.rotation = Quaternion.Euler(0, 0, 180);
            }

            UpdateHealthBar();
        }

        private void Update()
        {
            if (unitData == null) return;

            // Sync position (BattleManager updates the data, we just sync visuals)
            transform.position = unitData.position;

            // Check for damage
            if (unitData.currentHealth < lastHealth)
            {
                OnDamaged(lastHealth - unitData.currentHealth);
                lastHealth = unitData.currentHealth;
            }

            // Update animations
            UpdateAnimations();

            // Update health bar
            UpdateHealthBar();
        }

        private void UpdateAnimations()
        {
            if (animator == null) return;

            // Set moving state
            bool isMoving = unitData.targetUnit != null || unitData.targetTower != null;
            animator.SetBool("IsMoving", isMoving);

            // Set attacking state
            bool isAttacking = unitData.attackCooldown > 0.5f / unitData.cardDef.attackSpeed;
            animator.SetBool("IsAttacking", isAttacking);
        }

        private void UpdateHealthBar()
        {
            if (healthBarFill == null) return;

            float healthPercent = (float)unitData.currentHealth / unitData.maxHealth;

            // Scale the health bar
            healthBarFill.transform.localScale = new Vector3(healthPercent, 1, 1);

            // Color based on health
            if (healthPercent > 0.5f)
                healthBarFill.color = Color.green;
            else if (healthPercent > 0.25f)
                healthBarFill.color = Color.yellow;
            else
                healthBarFill.color = Color.red;
        }

        private void OnDamaged(int damage)
        {
            // Play hit effect
            if (hitEffect != null)
            {
                hitEffect.Play();
            }

            // Flash red
            StartCoroutine(DamageFlash());

            // Play hit animation
            if (animator != null)
            {
                animator.SetTrigger("Hit");
            }
        }

        private System.Collections.IEnumerator DamageFlash()
        {
            if (spriteRenderer == null) yield break;

            Color originalColor = spriteRenderer.color;
            spriteRenderer.color = Color.red;
            yield return new WaitForSeconds(0.1f);
            spriteRenderer.color = originalColor;
        }

        public void OnDeath()
        {
            // Play death effect
            if (deathEffect != null)
            {
                deathEffect.transform.SetParent(null);
                deathEffect.Play();
                Destroy(deathEffect.gameObject, 2f);
            }

            // Play death animation
            if (animator != null)
            {
                animator.SetTrigger("Death");
            }
        }
    }

    public class TowerBehaviour : MonoBehaviour
    {
        [Header("Visual References")]
        [SerializeField] private SpriteRenderer spriteRenderer;
        [SerializeField] private SpriteRenderer healthBarFill;
        [SerializeField] private Transform attackOrigin;
        [SerializeField] private ParticleSystem attackEffect;
        [SerializeField] private ParticleSystem damageEffect;
        [SerializeField] private ParticleSystem destroyEffect;
        [SerializeField] private GameObject activationIndicator;

        [Header("Settings")]
        [SerializeField] private Color playerColor = new Color(0.2f, 0.4f, 1f);
        [SerializeField] private Color opponentColor = new Color(1f, 0.3f, 0.2f);

        private Tower towerData;
        private bool isOpponent;
        private int lastHealth;

        public Tower Data => towerData;

        public void Initialize(Tower data, bool opponent)
        {
            towerData = data;
            isOpponent = opponent;
            lastHealth = data.currentHealth;

            // Set team color
            if (spriteRenderer != null)
            {
                spriteRenderer.color = opponent ? opponentColor : playerColor;
            }

            // King tower activation indicator
            if (activationIndicator != null)
            {
                activationIndicator.SetActive(data.isActivated);
            }

            UpdateHealthBar();
        }

        private void Update()
        {
            if (towerData == null) return;

            // Check for damage
            if (towerData.currentHealth < lastHealth)
            {
                OnDamaged(lastHealth - towerData.currentHealth);
                lastHealth = towerData.currentHealth;
            }

            // Check for destruction
            if (towerData.isDestroyed && gameObject.activeSelf)
            {
                OnDestroyed();
            }

            // Update activation state (for king tower)
            if (activationIndicator != null && towerData.type == TowerType.King)
            {
                activationIndicator.SetActive(towerData.isActivated);
            }

            UpdateHealthBar();
        }

        private void UpdateHealthBar()
        {
            if (healthBarFill == null || towerData == null) return;

            float healthPercent = towerData.HealthPercent;

            healthBarFill.transform.localScale = new Vector3(healthPercent, 1, 1);

            if (healthPercent > 0.5f)
                healthBarFill.color = Color.green;
            else if (healthPercent > 0.25f)
                healthBarFill.color = Color.yellow;
            else
                healthBarFill.color = Color.red;
        }

        private void OnDamaged(int damage)
        {
            if (damageEffect != null)
            {
                damageEffect.Play();
            }

            StartCoroutine(DamageFlash());
        }

        private System.Collections.IEnumerator DamageFlash()
        {
            if (spriteRenderer == null) yield break;

            Color originalColor = spriteRenderer.color;
            spriteRenderer.color = Color.white;
            yield return new WaitForSeconds(0.1f);
            spriteRenderer.color = originalColor;
        }

        private void OnDestroyed()
        {
            if (destroyEffect != null)
            {
                destroyEffect.transform.SetParent(null);
                destroyEffect.Play();
                Destroy(destroyEffect.gameObject, 3f);
            }

            // Hide or show destruction state
            gameObject.SetActive(false);
        }

        public void PlayAttackEffect(Vector3 targetPosition)
        {
            if (attackEffect != null)
            {
                attackEffect.Play();
            }
        }
    }
}
