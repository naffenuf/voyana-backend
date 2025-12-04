#!/usr/bin/env python3
"""
Quick test script to verify neighborhood cascading updates work correctly.
Run this inside the Docker container.
"""
import sys
from app import create_app, db
from app.models.neighborhood import NeighborhoodDescription
from app.models.tour import Tour
from app.models.site import Site

def test_cascading_update():
    """Test the cascading update logic."""
    app = create_app('development')

    with app.app_context():
        print("=== Testing Neighborhood Cascading Update ===\n")

        # Find a neighborhood with tours/sites to test
        print("1. Finding a neighborhood with tours...")
        neighborhoods = db.session.query(
            Tour.city,
            Tour.neighborhood,
            db.func.count(Tour.id).label('tour_count')
        ).filter(
            Tour.city.isnot(None),
            Tour.neighborhood.isnot(None)
        ).group_by(
            Tour.city,
            Tour.neighborhood
        ).having(
            db.func.count(Tour.id) > 0
        ).limit(1).all()

        if not neighborhoods:
            print("❌ No neighborhoods with tours found. Cannot test.")
            return False

        test_city, test_neighborhood, tour_count = neighborhoods[0]
        print(f"   Found: {test_city} / {test_neighborhood} ({tour_count} tours)")

        # Check for sites in this neighborhood
        site_count = Site.query.filter(
            Site.city == test_city,
            Site.neighborhood == test_neighborhood
        ).count()
        print(f"   Sites in neighborhood: {site_count}")

        # Check if description exists
        desc = NeighborhoodDescription.query.filter_by(
            city=test_city,
            neighborhood=test_neighborhood
        ).first()

        if not desc:
            print("   No description exists - creating one for testing...")
            desc = NeighborhoodDescription(
                city=test_city,
                neighborhood=test_neighborhood,
                description="Test description for cascading update"
            )
            db.session.add(desc)
            db.session.commit()
            print(f"   ✓ Created description ID {desc.id}")
        else:
            print(f"   ✓ Description exists (ID {desc.id})")

        # Now test the cascading update logic
        print("\n2. Testing cascading update (rename neighborhood)...")

        # Generate a test name (add " Test" to neighborhood name)
        new_neighborhood = f"{test_neighborhood} Test"

        # Check if test name already exists (cleanup from previous run)
        existing_test = NeighborhoodDescription.query.filter_by(
            city=test_city,
            neighborhood=new_neighborhood
        ).first()

        if existing_test:
            print(f"   Cleaning up previous test: deleting {new_neighborhood}...")
            db.session.delete(existing_test)
            db.session.commit()

        print(f"   Old name: {test_city} / {test_neighborhood}")
        print(f"   New name: {test_city} / {new_neighborhood}")

        # Count tours/sites BEFORE update
        tours_before = Tour.query.filter(
            Tour.city == test_city,
            Tour.neighborhood == test_neighborhood
        ).count()

        sites_before = Site.query.filter(
            Site.city == test_city,
            Site.neighborhood == test_neighborhood
        ).count()

        print(f"   Before: {tours_before} tours, {sites_before} sites")

        # Perform the update (simulating what the API does)
        old_city = desc.city
        old_neighborhood = desc.neighborhood

        # Update tours
        tours_updated = Tour.query.filter(
            Tour.city == old_city,
            Tour.neighborhood == old_neighborhood
        ).update(
            {Tour.city: test_city, Tour.neighborhood: new_neighborhood},
            synchronize_session=False
        )

        # Update sites
        sites_updated = Site.query.filter(
            Site.city == old_city,
            Site.neighborhood == old_neighborhood
        ).update(
            {Site.city: test_city, Site.neighborhood: new_neighborhood},
            synchronize_session=False
        )

        # Update description
        desc.neighborhood = new_neighborhood

        db.session.commit()

        print(f"   ✓ Updated {tours_updated} tours, {sites_updated} sites")

        # Verify the update
        print("\n3. Verifying updates...")

        tours_after_old = Tour.query.filter(
            Tour.city == test_city,
            Tour.neighborhood == test_neighborhood
        ).count()

        tours_after_new = Tour.query.filter(
            Tour.city == test_city,
            Tour.neighborhood == new_neighborhood
        ).count()

        sites_after_old = Site.query.filter(
            Site.city == test_city,
            Site.neighborhood == test_neighborhood
        ).count()

        sites_after_new = Site.query.filter(
            Site.city == test_city,
            Site.neighborhood == new_neighborhood
        ).count()

        print(f"   Old name ({test_neighborhood}): {tours_after_old} tours, {sites_after_old} sites")
        print(f"   New name ({new_neighborhood}): {tours_after_new} tours, {sites_after_new} sites")

        # Check if all moved correctly
        success = (
            tours_after_old == 0 and
            sites_after_old == 0 and
            tours_after_new == tours_before and
            sites_after_new == sites_before
        )

        if success:
            print("\n✅ Cascading update works correctly!")
        else:
            print("\n❌ Cascading update failed - some records didn't move")

        # Cleanup: revert changes
        print("\n4. Cleaning up (reverting changes)...")

        Tour.query.filter(
            Tour.city == test_city,
            Tour.neighborhood == new_neighborhood
        ).update(
            {Tour.neighborhood: test_neighborhood},
            synchronize_session=False
        )

        Site.query.filter(
            Site.city == test_city,
            Site.neighborhood == new_neighborhood
        ).update(
            {Site.neighborhood: test_neighborhood},
            synchronize_session=False
        )

        desc.neighborhood = test_neighborhood
        db.session.commit()

        print("   ✓ Reverted all changes")

        return success

if __name__ == '__main__':
    success = test_cascading_update()
    sys.exit(0 if success else 1)
